from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, CommandViewSet, PresetViewSet

router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'commands', CommandViewSet, basename='command')
router.register(r'presets', PresetViewSet, basename='preset')

urlpatterns = [
    path('', include(router.urls)),
]
