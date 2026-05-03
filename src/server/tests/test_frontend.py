import pytest
from django.urls import reverse
from api.models import Tbl_Device

@pytest.mark.django_db
class TestFrontendViews:
    def test_dashboard_view(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='frontuser', password='pass123')
        client.force_login(user)
        url = reverse('dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert 'SuperPersonal' in str(response.content)
        assert 'No Devices Connected' in str(response.content)

    def test_device_detail_view(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='frontuser2', password='pass123')
        client.force_login(user)
        device = Tbl_Device.objects.create(hardware_id="front-device", hostname="FrontHost")
        url = reverse('device_detail', args=[device.pk_device_id])
        response = client.get(url)
        assert response.status_code == 200
        assert 'FrontHost' in str(response.content)
