import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestDashboardAuth:
    def test_dashboard_redirects_unauthenticated(self, client):
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_dashboard_accessible_when_logged_in(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='viewer', password='pass123')
        client.force_login(user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
