import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import ws.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_personal.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            ws.routing.websocket_urlpatterns
        )
    ),
})
