import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    client = APIClient()
    user = User.objects.create_user(username='testuser', password='testpass123')
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_api_client():
    return APIClient()
