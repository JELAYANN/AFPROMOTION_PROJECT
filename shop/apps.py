from django.apps import AppConfig # type: ignore

class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        # BARIS INI WAJIB ADA AGAR SIGNAL JALAN
        import shop.signals