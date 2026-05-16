# core/apps.py

from django.apps import AppConfig


class CoreConfig(AppConfig):
    # Use BigAutoField as default primary key type for all models in this app
    default_auto_field = 'django.db.models.BigAutoField'
    
    # The name must match the app directory name
    name = 'core'
    
    # Human-readable name for the app (shown in Django admin)
    verbose_name = 'Vape Cluster Core'
    
    def ready(self):
        """
        This method runs when the app is fully loaded.
        Used to register signals for the core app.
        Signals handle events like:
        - User registration (send welcome email)
        - Order placement (send confirmation)
        - Cart updates (sync with session)
        """
        try:
            # Import signals so they get connected when app starts
            import core.signals  # noqa: F401
        except ImportError:
            # Signals file may not exist yet — safe to skip
            pass