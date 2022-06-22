from django.urls import re_path
from wss.consumers import VccsConsumer

channel_routing = [
    re_path(r'^connect/$', VccsConsumer.as_asgi()),
]