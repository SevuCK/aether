import pytest
from unittest.mock import patch, MagicMock
from netutil import NetworkUtility

@pytest.fixture
def net_util():
    return NetworkUtility()

@patch('netutil.Controller')
def test_start_onion_service_success(mock_controller_class, net_util):
    """Prüft, ob der Tor Hidden Service mit den richtigen Parametern gestartet wird."""

    mock_controller_instance = MagicMock()

    mock_controller_class.from_port.return_value = mock_controller_instance

    mock_controller_instance.get_info.return_value = "PROGRESS=100 SUMMARY=Done"

    mock_response = MagicMock()
    mock_response.service_id = "mocked_onion_address"
    mock_response.private_key = "mocked_private_key"
    mock_response.private_key_type = "ED25519-V3"
    mock_controller_instance.create_ephemeral_hidden_service.return_value = mock_response

    onion, key_type, priv_key = net_util.start_onion_service(flask_port=5000)

    assert onion == "mocked_onion_address"
    assert priv_key == "mocked_private_key"
    assert key_type == "ED25519-V3"

    mock_controller_instance.create_ephemeral_hidden_service.assert_called_once()

@patch('netutil.Controller')
def test_start_onion_service_failure(mock_controller_class, net_util):
    """Prüft, ob Fehler robust abgefangen werden."""

    from stem import SocketError
    mock_controller_class.from_port.side_effect = SocketError("Connection refused")

    onion, key_type, priv_key = net_util.start_onion_service(flask_port=5000)

    assert onion is None
    assert priv_key is None

@patch('netutil.requests.Session.post')
def test_send_message_success(mock_post, net_util):
    """Prüft das erfolgreiche Senden einer P2P Nachricht."""
    # Simuliere einen 200 OK Response vom Empfänger
    mock_post.return_value.status_code = 200

    result = net_util.send_message("http://target.onion", {"content": "Hallo!"})

    assert result is True
    mock_post.assert_called_once()

@patch('netutil.requests.Session.post')
def test_send_message_failure(mock_post, net_util):
    """Prüft, ob HTTP-Fehler vom Empfänger (z.B. 500) abgefangen werden."""
    mock_post.return_value.status_code = 500

    result = net_util.send_message("target.onion", {"content": "Hallo!"})

    assert result is False

@patch('netutil.requests.Session.post')
def test_send_message_offline(mock_post, net_util):
    """Prüft, ob das Backend nicht abstürzt, wenn der Kontakt offline ist."""
    from requests.exceptions import ConnectionError
    # Simuliere einen Tor Connection Timeout/Error
    mock_post.side_effect = ConnectionError("Node offline")

    result = net_util.send_message("target.onion", {"content": "Hallo!"})

    assert result is False

def test_stop(net_util):
    """Prüft den Graceful Shutdown des Tor Daemons."""
    net_util.controller = MagicMock()
    net_util.stop()
    net_util.controller.close.assert_called_once()