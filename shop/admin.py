from django.contrib import admin # type: ignore
from .models import ProductCategory, Product, ProductVariant, Color, Size

# 1. Ini yang membuat tabel stok muncul di dalam halaman Produk
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1  # Jumlah baris kosong otomatis yang muncul
    fields = ('color', 'size', 'stock', 'price_override')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'total_stock', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    # Memasukkan tabel varian (warna/size) ke halaman produk
    inlines = [ProductVariantInline]

# 2. Daftarkan Master Data (Warna & Size) agar bisa dipilih di dropdown
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(ProductCategory)