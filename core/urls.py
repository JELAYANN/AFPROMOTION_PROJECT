from django.contrib import admin # type: ignore
from django.urls import path, include # type: ignore
from django.contrib.auth import views as auth_views      # type: ignore
from django.conf import settings # type: ignore
from django.conf.urls.static import static # type: ignore
from shop import views as shop_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('shop.urls', namespace='shop')),

    path('login/', auth_views.LoginView.as_view(
        template_name='shop/login.html'
    ), name='login'),
    path('register/', shop_views.register, name='register'),
    path('logout/', shop_views.logout_view, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
