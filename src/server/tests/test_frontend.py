import pytest
from django.urls import reverse
from api.models import Tbl_Device

@pytest.mark.django_db
class TestFrontendViews:
    def test_dashboard_view(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='frontuser', password='pass123')
        client.force_login(user)
        url = reverse('dock')
        response = client.get(url)
        assert response.status_code == 200
        assert 'dock' in str(response.content).lower()

    def test_device_detail_view(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='frontuser2', password='pass123')
        client.force_login(user)
        device = Tbl_Device.objects.create(hardware_id="front-device", hostname="FrontHost")
        url = reverse('dock_device', args=[device.pk_device_id])
        response = client.get(url)
        assert response.status_code == 200
        assert 'dock' in str(response.content).lower()
