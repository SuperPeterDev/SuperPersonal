import pytest
from rest_framework import status
from django.urls import reverse
from api.models import Tbl_Device, Tbl_Command, CommandType, CommandStatus

@pytest.mark.django_db
class TestDeviceAPI:
    def test_register_device(self, api_client):
        url = reverse('device-list') # Assuming DRF Router
        data = {
            "hardware_id": "api-test-device",
            "hostname": "API Host",
            "os_config": {"os": "Linux"}
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Tbl_Device.objects.count() == 1
        assert Tbl_Device.objects.get().hardware_id == "api-test-device"

@pytest.mark.django_db
class TestCommandAPI:
    def test_list_pending_commands(self, api_client):
        # Setup
        device = Tbl_Device.objects.create(hardware_id="cmd-device")
        Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING, status=CommandStatus.PENDING)
        Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING, status=CommandStatus.SUCCESS)
        
        url = reverse('command-pending') + f"?device_id={device.hardware_id}"
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        # After poll, status should be SENT (not PENDING)
        assert response.data[0]['status'] == 'SENT'

    def test_pending_endpoint_marks_commands_sent(self, api_client):
        device = Tbl_Device.objects.create(hardware_id="sent-test-device")
        Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING, status=CommandStatus.PENDING)

        url = reverse('command-pending') + f"?device_id={device.hardware_id}"
        api_client.get(url)

        # After polling, the command must be SENT — not PENDING
        cmd = Tbl_Command.objects.get()
        assert cmd.status == CommandStatus.SENT

    def test_submit_result(self, api_client):
        device = Tbl_Device.objects.create(hardware_id="res-device")
        cmd = Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING)
        
        url = reverse('command-result', args=[cmd.pk])
        data = {
            "status": "SUCCESS",
            "log": {"output": "Pong"}
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        cmd.refresh_from_db()
        assert cmd.status == "SUCCESS"
        assert hasattr(cmd, 'log')
        assert cmd.log.output == "Pong"

    def test_result_ws_message_includes_command_type(self, api_client):
        from unittest.mock import patch
        device = Tbl_Device.objects.create(hardware_id="ws-type-device")
        cmd = Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING)

        url = reverse('command-result', args=[cmd.pk])
        data = {"status": "SUCCESS", "log": {"output": "Pong"}}

        with patch('api.views.async_to_sync') as mock_async:
            api_client.post(url, data, format='json')
            inner_call = mock_async.return_value
            ws_payload = inner_call.call_args[0][1]
            assert ws_payload['data']['type'] == CommandType.CMD_PING

    def test_pending_endpoint_accessible_without_auth(self, unauthenticated_api_client):
        device = Tbl_Device.objects.create(hardware_id="noauth-poll-device")
        url = reverse('command-pending') + f"?device_id={device.hardware_id}"
        response = unauthenticated_api_client.get(url)
        assert response.status_code == 200

    def test_result_endpoint_accessible_without_auth(self, unauthenticated_api_client):
        device = Tbl_Device.objects.create(hardware_id="noauth-res-device")
        cmd = Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING)
        url = reverse('command-result', args=[cmd.pk])
        response = unauthenticated_api_client.post(url, {"status": "SUCCESS", "log": {"output": "Pong"}}, format='json')
        assert response.status_code == 200

    def test_device_registration_accessible_without_auth(self, unauthenticated_api_client):
        url = reverse('device-list')
        data = {"hardware_id": "noauth-device", "hostname": "NoAuth Host", "os_config": {}}
        response = unauthenticated_api_client.post(url, data, format='json')
        assert response.status_code == 201

    def test_command_create_rejects_unauthenticated(self, unauthenticated_api_client):
        device = Tbl_Device.objects.create(hardware_id="reject-device")
        url = reverse('command-list')
        data = {"device": str(device.pk_device_id), "command_type": "CMD_PING"}
        response = unauthenticated_api_client.post(url, data, format='json')
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestPresetAPI:
    def test_create_preset(self, api_client):
        url = reverse('preset-list')
        data = {"name": "Test Preset", "url": "http://example.com"}
        response = api_client.post(url, data, format='json')
        print(response.content) # Debugging if 404
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestAuthProtection:
    def test_unauthenticated_command_creation_rejected(self, unauthenticated_api_client):
        device = Tbl_Device.objects.create(hardware_id="auth-test-device")
        url = reverse('command-list')
        data = {"device": str(device.pk_device_id), "command_type": "CMD_PING"}
        response = unauthenticated_api_client.post(url, data, format='json')
        assert response.status_code in [401, 403]

    def test_authenticated_command_creation_allowed(self, api_client):
        device = Tbl_Device.objects.create(hardware_id="auth-ok-device")
        url = reverse('command-list')
        data = {"device": str(device.pk_device_id), "command_type": "CMD_PING", "payload": {}}
        response = api_client.post(url, data, format='json')
        assert response.status_code == 201
