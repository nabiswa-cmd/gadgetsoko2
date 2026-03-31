from django.apps import AppConfig

def ready(self):
    import app.signals


class AppConfig(AppConfig):
    name = 'app'
