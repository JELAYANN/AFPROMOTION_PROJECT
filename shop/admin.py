from django.contrib import admin # type: ignore
from django.utils.html import format_html # type: ignore
from decimal import Decimal
from .models import (
    Customer, ProductCategory, Product, ProductVariant, 
    Color, Size, Order, OrderItem,
    CustomService, CustomProduct, CustomProductVariant, Payment
)

# --- 1. SETTING PRODUK KUSTOM (SABLON/BORDIR) ---

class CustomProductVariantInline(admin.TabularInline):
    model = CustomProductVariant
    extra = 1
    fields = ('size', 'price', 'stock')

@admin.register(CustomProduct)
class CustomProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_product', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'base_product__name')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('available_services',)
    # Menampilkan input harga per ukuran di dalam halaman Custom Product
    inlines = [CustomProductVariantInline]

@admin.register(CustomService)
class CustomServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_type', 'additional_price')
    list_filter = ('service_type',)
    search_fields = ('name',)


# --- 2. SETTING PRODUK STANDAR (POLOS) ---

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('color', 'size', 'stock', 'price_override')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # 'total_stock' dihapus karena sudah tidak ada di models.py
    list_display = ('name', 'category', 'price', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]


# --- 3. SETTING TRANSAKSI (ORDER) ---

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Field 'variant' dihapus dari readonly karena strukturnya berubah
    readonly_fields = (
        'product', 'quantity', 'unit_price', 
        'variant_label', 'is_custom', 'custom_service_name', 
        'custom_price', 'display_custom_image', 'custom_notes', 'line_total'
    )
    fields = (
        'product', 'variant_label', 'quantity', 'unit_price', 
        'is_custom', 'custom_service_name', 'custom_price', 
        'display_custom_image', 'custom_notes', 'line_total'
    )
    can_delete = False

    def display_custom_image(self, obj):
        if obj.custom_image:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" width="50" height="50" style="object-fit:cover; border-radius:5px;" /></a>', obj.custom_image.url)
        return "-"
    display_custom_image.short_description = "Desain Custom"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # 'shipping_status' dihapus karena tidak ada di models.py
    list_display = ('id', 'customer', 'status', 'total', 'created_at')
    list_filter = ('status', 'created_at')
    list_editable = ('status',)
    search_fields = ('id', 'customer__user__username', 'shipping_name')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informasi Utama', {
            'fields': ('customer', 'status', 'subtotal', 'shipping_cost', 'total')
        }),
        ('Data Pengiriman', {
            'fields': ('shipping_name', 'shipping_phone', 'shipping_address', 
                    'shipping_city', 'shipping_province', 'shipping_postal_code')
        }),
        ('Ekspedisi & Resi', {
            'fields': ('courier_code', 'courier_service', 'tracking_number')
        }),
    )


# --- 4. MASTER DATA LAINNYA ---

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'status', 'created_at')

admin.site.register(ProductCategory)