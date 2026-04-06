from django.contrib import admin # type: ignore
from decimal import Decimal
from .models import (
    ProductCategory, Product, ProductVariant, 
    Color, Size, Order, OrderItem
)

# 1. Tabel Detail Barang (Muncul di dalam halaman Order)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'variant', 'quantity', 'unit_price', 'variant_label', 'line_total')
    can_delete = False

# 2. Pengaturan Tampilan Pesanan (ORDER)
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Kolom utama di daftar pesanan
    list_display = ('id', 'customer', 'status', 'shipping_status', 'total', 'created_at')
    
    # Filter samping
    list_filter = ('status', 'shipping_status', 'created_at')
    
    # Bisa ganti status pembayaran & pengiriman langsung di tabel depan
    list_editable = ('status', 'shipping_status')
    
    # Pencarian berdasarkan ID atau nama customer
    search_fields = ('id', 'customer__user__username', 'shipping_name')
    
    # Masukkan detail barang ke dalam halaman order
    inlines = [OrderItemInline]
    
    # Mengurutkan dari yang paling baru
    ordering = ('-created_at',)
    
    # Mengelompokkan tampilan di dalam detail order agar rapi
    fieldsets = (
        ('Informasi Utama', {
            'fields': ('customer', 'status', 'total')
        }),
        ('Data Pengiriman', {
            'fields': ('shipping_name', 'shipping_phone', 'shipping_address', 
                    'shipping_city', 'shipping_province', 'shipping_postal_code')
        }),
        ('Ekspedisi & Resi', {
            'fields': ('courier_code', 'courier_service', 'shipping_status', 'tracking_number')
        }),
    )

# --- Sisanya tetap sama seperti sebelumnya ---

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('color', 'size', 'stock', 'price_override')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'total_stock', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(ProductCategory)