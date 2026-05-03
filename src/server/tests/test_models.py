import pytest
from api.models import Tbl_Device, Tbl_Command, Tbl_Preset, CommandType, CommandStatus
from django.utils import timezone
from datetime import timedelta

@pytest.mark.django_db
class TestDeviceModel:
    def test_create_device(self):
        device = Tbl_Device.objects.create(
            hardware_id="test-uuid-123",
            hostname="Test PC",
            os_config={"os": "Windows 11"}
        )
        assert device.pk is not None
        assert device.hardware_id == "test-uuid-123"
        assert device.is_active is True

    def test_duplicate_hardware_id(self):
        Tbl_Device.objects.create(hardware_id="unique-id")
        with pytest.raises(Exception): # IntegrityError
            Tbl_Device.objects.create(hardware_id="unique-id")

@pytest.mark.django_db
class TestCommandModel:
    def test_create_command(self):
        device = Tbl_Device.objects.create(hardware_id="cmd-device")
        cmd = Tbl_Command.objects.create(
            device=device,
            command_type=CommandType.CMD_PING,
            payload={}
        )
        assert cmd.status == CommandStatus.PENDING
        assert cmd.created_at is not None

    def test_command_defaults(self):
        """Test that default status is PENDING and dates are handled"""
        device = Tbl_Device.objects.create(hardware_id="defaults-device")
        cmd = Tbl_Command.objects.create(device=device, command_type="CMD_TEST")
        assert cmd.status == CommandStatus.PENDING
        assert cmd.executed_at is None

@pytest.mark.django_db
class TestScheduledCommand:
    def test_command_has_scheduled_for_field(self):
        device = Tbl_Device.objects.create(hardware_id="sched-device")
        future = timezone.now() + timedelta(minutes=30)
        cmd = Tbl_Command.objects.create(
            device=device,
            command_type=CommandType.CMD_PING,
            status=CommandStatus.PENDING,
            scheduled_for=future
        )
        cmd.refresh_from_db()
        assert cmd.scheduled_for is not None

    def test_command_scheduled_for_defaults_null(self):
        device = Tbl_Device.objects.create(hardware_id="nosched-device")
        cmd = Tbl_Command.objects.create(device=device, command_type=CommandType.CMD_PING)
        assert cmd.scheduled_for is None

@pytest.mark.django_db
class TestPresetModel:
    def test_create_preset(self):
        preset = Tbl_Preset.objects.create(
            name="LoFi",
            url="https://youtube.com/watch?v=123"
        )
        assert preset.name == "LoFi"
