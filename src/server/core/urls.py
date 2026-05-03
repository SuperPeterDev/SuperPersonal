from django.urls import path
from . import views

urlpatterns = [
    path('', views.dock, name='dock'),
    path('device/<uuid:pk>/', views.dock_device, name='dock_device'),
]
