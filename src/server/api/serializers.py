from rest_framework import serializers
from .models import Tbl_Device, Tbl_Command, Tbl_Preset, Tbl_CommandLog

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tbl_Device
        fields = '__all__'

class CommandLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tbl_CommandLog
        fields = '__all__'

class CommandSerializer(serializers.ModelSerializer):
    log = CommandLogSerializer(read_only=True)

    class Meta:
        model = Tbl_Command
        fields = '__all__'

class PresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tbl_Preset
        fields = '__all__'
