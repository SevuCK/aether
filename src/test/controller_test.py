import pytest
import controller
from unittest.mock import patch, mock_open

def test_register_success(client, mock_db, mock_net):
    mock_net.start_onion_service.return_value = ("onion_vww6yba...", "ED25519-V3", "priv_key")

    response = client.post(
        "/api/v1/auth/register",
        json={"username": "Alice", "password": "SecurePassword123"}
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["status"] == "success"
    assert data["onion_address"] == "onion_vww6yba..."
    mock_db.save_identity.assert_called_once_with("onion_vww6yba...", "priv_key", "Alice")

def test_login_success(client, mock_db, mock_net):
    mock_db.load_identity.return_value = {
        "onion_address": "onion_vww6yba...",
        "ed25519_private_key": "priv_key"
    }
    controller.my_onion_address = None
    mock_net.start_onion_service.return_value = ("onion_vww6yba...", "ED25519-V3", "priv_key")

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "Alice", "password": "SecurePassword123"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"

def test_login_failure(client, mock_db):
    mock_db.load_identity.return_value = None

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "Alice", "password": "WrongPassword"}
    )

    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data

def test_get_contacts(client, mock_db):
    mock_conn = mock_db._get_conn.return_value.__enter__.return_value
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [
        {"id": 1, "onion_address": "bob_onion...", "display_name": "Bob"}
    ]

    response = client.get("/api/v1/contacts")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["display_name"] == "Bob"

def test_add_contact(client, mock_db):
    mock_db.create_contact.return_value = (2, 99)

    response = client.post(
        "/api/v1/contacts",
        json={"onion_address": "new_onion...", "display_name": "Charlie"}
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] == 2
    mock_db.create_contact.assert_called_once_with("Charlie", "new_onion...")

def test_send_message(client, mock_db):
    mock_db.save_message.return_value = 99

    response = client.post(
        "/api/v1/messages",
        json={"chat_id": 1, "content": "Hallo Tor!"}
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["message_id"] == 99
    assert data["status"] == "OUTGOING_CREATED"

def test_system_status(client):
    controller.my_onion_address = "onion_vww6yba..."

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    data = response.get_json()
    assert data["tor_bootstrap_percent"] == 100
    assert data["status"] == "ready"

def test_receive_message_known_contact(client, mock_db):
    mock_db.get_chat_id_by_onion.return_value = 99
    mock_cursor = mock_db._get_conn.return_value.__enter__.return_value.cursor.return_value
    mock_cursor.fetchone.return_value = {'id': 5}

    response = client.post("/api/receive_message", json={
        "sender_onion": "known_onion_address",
        "text": "Hello from the Tor network!",
        "timestamp": "2026-04-06T12:00:00Z"
    })

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    mock_db.save_message.assert_called_once()

def test_receive_message_unknown_contact(client, mock_db):
    mock_db.get_chat_id_by_onion.return_value = None

    response = client.post("/api/receive_message", json={
        "sender_onion": "unknown_hacker_onion",
        "text": "Malicious spam!"
    })

    assert response.status_code == 403
    assert response.get_json()["error"] == "Unauthorized / Unknown Contact"

def test_register_missing_data(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"password": "OnlyPassword"}
    )
    assert response.status_code == 400
    assert "error" in response.get_json()

def test_middleware_api_key_rejected(client):
    controller.REQUIRE_API_KEY = True
    controller.EPHEMERAL_API_KEY = "secret-key"

    response = client.get("/api/v1/system/status", headers={"X-Aether-API-Key": "wrong-key"})

    assert response.status_code == 401

    controller.REQUIRE_API_KEY = False