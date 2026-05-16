# vape_cluster/asgi.py
# ASGI config for vape_cluster project.
# This file exposes the ASGI callable as a module-level variable named 'application'.
# It supports both HTTP and WebSocket connections.

import os

from django.core.asgi import get_asgi_application

# Set the default Django settings module for the 'asgi' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vape_cluster.settings')

# Get the ASGI application handler for HTTP requests
application = get_asgi_application()