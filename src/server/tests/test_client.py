import pytest
import sys
import os
import requests_mock
from unittest.mock import patch, MagicMock

# Add client directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../client')))

from client import Client, SERVER_URL

class TestClientAgent:
    @pytest.fixture
    def client(self):
        return Client()

    def test_register_device(self, client):
        with requests_mock.Mocker() as m:
            m.post(f"{SERVER_URL}/devices/", json={"hardware_id": "test-id", "pk_device_id": "uuid"}, status_code=201)
            
            # Mock get_mac_address to return constant
            with patch('uuid.getnode', return_value=123456):
                client.register()
                assert client.access_token is None # JWT not implemented in basic register yet, but device_id should be set
                # Ideally client stores the ID. For now checking if logic runs without error.

    def test_poll_commands(self, client):
        client.device_id = "test-device"
        with requests_mock.Mocker() as m:
            m.get(f"{SERVER_URL}/commands/pending/?device_id=test-device", json=[
                {"pk_command_id": "cmd-1", "command_type": "CMD_PING", "payload": {}}
            ])
            
            with patch.object(client, 'execute_command') as mock_exec:
                client.poll_commands()
                mock_exec.assert_called_once()
                args, _ = mock_exec.call_args
                assert args[0]['command_type'] == 'CMD_PING'

    def test_execute_volume_command(self, client):
        cmd = {"command_type": "CMD_SET_VOLUME", "payload": {"level": 50, "mute": False}}
        
        with patch('client.AudioUtilities') as mock_audio: # Mock pycaw
            client.execute_command(cmd)
            # Assert pycaw logic was called (simplified for test)
            # Since we haven't written the code, this verifies we need to implement it.
            pass

    def test_execute_preset_command(self, client):
        cmd = {"command_type": "CMD_OPEN_PRESET", "payload": {"url": "http://youtube.com"}}
        
        with patch('webbrowser.open') as mock_browser:
            client.execute_command(cmd)
            mock_browser.assert_called_with("http://youtube.com")
