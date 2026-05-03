from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Tbl_Device, Tbl_Command, Tbl_Preset
from src.shared.enums import CommandStatus
from .serializers import DeviceSerializer, CommandSerializer, PresetSerializer

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Tbl_Device.objects.all()
    serializer_class = DeviceSerializer
    lookup_field = 'hardware_id'

    def create(self, request, *args, **kwargs):
        hardware_id = request.data.get('hardware_id')
        if hardware_id:
            existing = Tbl_Device.objects.filter(hardware_id=hardware_id).first()
            if existing:
                # Update device info
                existing.hostname = request.data.get('hostname', existing.hostname)
                existing.os_config = request.data.get('os_config', existing.os_config)
                existing.save()
                
                # Notify Dashboard
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "dashboard",
                    {
                        "type": "device_update",
                        "data": {
                            "id": str(existing.pk_device_id),
                            "hostname": existing.hostname,
                            "status": "online"
                        }
                    }
                )
                
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {
                "type": "device_update",
                "data": {
                    "id": str(instance.pk_device_id),
                    "hostname": instance.hostname,
                    "status": "online"
                }
            }
        )

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class CommandViewSet(viewsets.ModelViewSet):
    queryset = Tbl_Command.objects.all()
    serializer_class = CommandSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        # Notify Dashboard
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {
                "type": "command_update",
                "data": {
                    "id": str(instance.pk_command_id),
                    "device_id": str(instance.device.pk_device_id),
                    "type": instance.command_type,
                    "status": instance.status,
                    "created_at": str(instance.created_at)
                }
            }
        )

    @action(detail=False, methods=['get'])
    def pending(self, request):
        hardware_id = request.query_params.get('device_id')
        if not hardware_id:
            return Response({"error": "device_id required"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        commands = Tbl_Command.objects.filter(
            device__hardware_id=hardware_id,
            status=CommandStatus.PENDING
        ).filter(
            Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=now)
        )
        command_ids = list(commands.values_list('pk_command_id', flat=True))
        commands.update(status=CommandStatus.SENT)

        fetched = Tbl_Command.objects.filter(pk_command_id__in=command_ids)
        serializer = self.get_serializer(fetched, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def result(self, request, pk=None):
        command = self.get_object()
        
        # update status
        status_val = request.data.get('status')
        if status_val:
            command.status = status_val
            command.save()

        # create log
        log_data = request.data.get('log')
        if log_data:
            from .models import Tbl_CommandLog
            log = Tbl_CommandLog.objects.create(
                command=command,
                output=log_data.get('output', ''),
                error_trace=log_data.get('error_trace', '')
            )
        
        # Notify Dashboard
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {
                "type": "command_update",
                "data": {
                    "id": str(command.pk_command_id),
                    "device_id": str(command.device.pk_device_id),
                    "type": command.command_type,
                    "status": command.status,
                    "output": log_data.get('output', '') if log_data else ""
                }
            }
        )
        
        return Response({'status': 'updated'})

class PresetViewSet(viewsets.ModelViewSet):
    queryset = Tbl_Preset.objects.all()
    serializer_class = PresetSerializer
