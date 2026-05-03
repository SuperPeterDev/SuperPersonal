import pytest
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
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

    def test_pending_excludes_future_scheduled_commands(self, api_client):
        device = Tbl_Device.objects.create(hardware_id="sched-filter-device")
        # This one should be returned (no schedule)
        Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING, status=CommandStatus.PENDING)
        # This one should NOT be returned (scheduled for the future)
        future = timezone.now() + timedelta(hours=1)
        Tbl_Command.objects.create(
            device=device, command_type=CommandType.CMD_PING,
            status=CommandStatus.PENDING, scheduled_for=future
        )

        url = reverse('command-pending') + f"?device_id={device.hardware_id}"
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_pending_includes_due_scheduled_commands(self, api_client):
        device = Tbl_Device.objects.create(hardware_id="due-sched-device")
        past = timezone.now() - timedelta(minutes=5)
        Tbl_Command.objects.create(
            device=device, command_type=CommandType.CMD_PING,
            status=CommandStatus.PENDING, scheduled_for=past
        )

        url = reverse('command-pending') + f"?device_id={device.hardware_id}"
        response = api_client.get(url)

        assert len(response.data) == 1

@pytest.mark.django_db
class TestPresetAPI:
    def test_create_preset(self, api_client):
        url = reverse('preset-list')
        data = {"name": "Test Preset", "url": "http://example.com"}
        response = api_client.post(url, data, format='json')
        print(response.content) # Debugging if 404
        assert response.status_code == status.HTTP_201_CREATED
