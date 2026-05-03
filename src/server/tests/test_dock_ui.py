import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestDockUIRenders:
    def test_dock_page_returns_200_when_logged_in(self):
        user = User.objects.create_user(username='dockuser', password='pass123')
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dock'))
        assert response.status_code == 200
        assert 'dock' in response.content.decode().lower()

    def test_dock_device_page_returns_200_when_logged_in(self):
        from api.models import Tbl_Device
        device = Tbl_Device.objects.create(hardware_id='dock-device', hostname='TestDock')
        user = User.objects.create_user(username='dockuser2', password='pass123')
        client = Client()
        client.force_login(user)
        response = client.get(reverse('dock_device', args=[device.pk_device_id]))
        assert response.status_code == 200
        assert 'dock' in response.content.decode().lower()

    def test_dock_page_redirects_when_unauthenticated(self):
        client = Client()
        response = client.get(reverse('dock'))
        assert response.status_code == 302
