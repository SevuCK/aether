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