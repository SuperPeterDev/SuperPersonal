import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from src.shared.enums import CommandType, CommandStatus

# Removing local TextChoices as we now use shared Enums
# Django 5+ handles Enums in choices nicely, but to be safe and strictly match db strings:
# We can use a helper or just list comprehension if they are StrEnum.
# They are (str, Enum), so they work directly with choices=CommandType.choices? 
# No, CommandType is Enum. CommandType.choices isn't auto-generated unless it's Django's TextChoices.
# We need to bridge it.
def enum_to_choices(enum_cls):
    return [(e.value, e.name) for e in enum_cls]

# Actually, if we want to keep using the class name in code like CommandType.CMD_PING, 
# we can alias it.


class Tbl_Device(models.Model):
    pk_device_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hardware_id = models.CharField(max_length=255, unique=True, db_index=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    os_config = models.JSONField(default=dict, blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.hostname} ({self.hardware_id})"

class Tbl_Preset(models.Model):
    pk_preset_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=1024)
    icon = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Tbl_Command(models.Model):
    pk_command_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Tbl_Device, on_delete=models.CASCADE, related_name='commands')
    command_type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in CommandType])
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(tag.value, tag.value) for tag in CommandStatus],
        default=CommandStatus.PENDING.value,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.command_type} -> {self.device.hostname}"

class Tbl_CommandLog(models.Model):
    pk_log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    command = models.OneToOneField(Tbl_Command, on_delete=models.CASCADE, related_name='log')
    output = models.TextField(blank=True, null=True)
    error_trace = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
