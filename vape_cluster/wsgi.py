# wsgi.py
# WSGI config for vape_cluster project.
# This file exposes the WSGI callable as a module-level variable named 'application'.
# Django uses this for deployment with WSGI-compatible web servers (e.g., Gunicorn, uWSGI).

import os

from django.core.wsgi import get_wsgi_application

# Set the default Django settings module for the WSGI application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vape_cluster.settings')

# Create the WSGI application callable
# Web servers will use this 'application' object to communicate with Django
application = get_wsgi_application()