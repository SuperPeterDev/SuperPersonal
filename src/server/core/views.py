from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from api.models import Tbl_Device


@login_required
def dock(request):
    from api.models import Tbl_Device
    first_device = Tbl_Device.objects.order_by('-last_seen').first()
    return render(request, 'core/dock.html', {
        'device': first_device,
        'devices': Tbl_Device.objects.all().order_by('-last_seen')
    })


@login_required
def dock_device(request, pk):
    from api.models import Tbl_Device
    device = get_object_or_404(Tbl_Device, pk=pk)
    return render(request, 'core/dock.html', {
        'device': device,
        'devices': Tbl_Device.objects.all().order_by('-last_seen')
    })
