from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from api.models import Tbl_Device, Tbl_Command, Tbl_Preset


@login_required
def dashboard(request):
    devices = Tbl_Device.objects.all().order_by('-last_seen')
    return render(request, 'core/dashboard.html', {'devices': devices})


@login_required
def device_detail(request, pk):
    device = get_object_or_404(Tbl_Device, pk=pk)
    presets = Tbl_Preset.objects.all()
    logs = Tbl_Command.objects.filter(device=device).select_related('log').order_by('-created_at')[:10]
    return render(request, 'core/detail.html', {
        'device': device,
        'presets': presets,
        'logs': logs
    })
