from django.apps import AppConfig


class ScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper'
    
    def ready(self):
        """Register signals when Django app is ready"""
        import scraper.signals  # noqa
