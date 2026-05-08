from django.urls import path # type: ignore
from . import views

app_name = 'shop'

urlpatterns = [
    # --- HALAMAN UTAMA & KATALOG ---
    path('', views.home, name='home'),
    path('katalog/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    
    # --- KATALOG CUSTOM ---
    path('custom/', views.custom_katalog, name='custom_katalog'),
    path('custom/<slug:slug>/', views.custom_product_detail, name='custom_product_detail'),

    # --- KERANJANG (CART) ---
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),

    # --- PROSES CHECKOUT & PEMBAYARAN ---
    # Alur: Checkout -> Order Pay (Midtrans) -> History
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/pay/', views.order_pay, name='order_pay'),
    path('payment/notification/', views.midtrans_callback, name='midtrans_callback'),
    path(
        'payment/success/<int:order_id>/',
        views.payment_success,
        name='payment_success'
    ),

    # --- INFORMASI PESANAN (USER) ---
    path('orders/', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    # --- PROFIL PENGGUNA ---
    path('profile/', views.profile, name='profile'),

    # --- MANAJEMEN / ADMIN DASHBOARD ---
    path('management/dashboard/', views.management_dashboard, name='management_dashboard'),
    path('management/orders/', views.management_order_list, name='management_order_list'),
    path('management/orders/<int:order_id>/', views.management_order_detail, name='management_order_detail'),
    path('management/orders/<int:order_id>/update/', views.management_order_update, name='management_order_update'),
    path('management/sales-report/', views.management_sales_report, name='management_sales_report'),
    path('management/sales-report/export/', views.management_sales_report_export, name='management_sales_report_export'),
]