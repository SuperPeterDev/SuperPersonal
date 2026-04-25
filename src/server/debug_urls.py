import os
import django
from django.urls import reverse
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "super_personal.settings")
django.setup()

try:
    print(f"device-list: {reverse('device-list')}")
except Exception as e:
    print(f"device-list error: {e}")

try:
    print(f"api:device-list: {reverse('api:device-list')}")
except Exception as e:
    print(f"api:device-list error: {e}")

from django.urls import get_resolver
print(get_resolver().url_patterns)
