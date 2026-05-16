#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.
Project: vape_cluster
Database: MySQL
"""
import os
import sys


def main():
    """
    Run administrative tasks for vape_cluster project.
    Sets the default Django settings module and executes command line arguments.
    """
    # Set the default settings module for the vape_cluster project
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vape_cluster.settings')

    try:
        # Import Django's execute_from_command_line utility
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Raise a helpful error if Django is not installed or not on PYTHONPATH
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Execute the command passed from the command line (e.g., runserver, migrate)
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    # Entry point: run main() when script is executed directly
    main()