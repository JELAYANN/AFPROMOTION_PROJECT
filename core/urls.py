from django.contrib import admin # type: ignore
from django.urls import path, include # type: ignore
from django.contrib.auth import views as auth_views # type: ignore
from django.conf import settings # type: ignore
from django.conf.urls.static import static # type: ignore
from shop import views as shop_views

# core/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),

    # 1. SATU-SATUNYA PINTU LOGIN & REGISTER
    # Allauth akan otomatis mencari file di 'account/login.html' dan 'account/signup.html'
    path('accounts/', include('allauth.urls')), 

    # 2. URL APLIKASI UTAMA
    path('', include('shop.urls', namespace='shop')),

    # CATATAN: Path login/, register/, dan logout/ manual DIHAPUS 
    # agar tidak tabrakan dengan sistem Allauth yang sudah kita setting bypass-nya.
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)