"""
ASGI config for vccs project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
import sys

sys.path.append("/var/www/vccs.vnpas.uk/vccs")
sys.path.append("/var/www/vccs.vnpas.uk/vccs/vccs")

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import wss.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vccs.settings')
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(wss.routing.channel_routing)),
})
