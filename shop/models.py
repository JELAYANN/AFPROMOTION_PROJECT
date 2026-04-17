from django.db import models # type: ignore
from django.contrib.auth.models import User # type: ignore
from django.utils.text import slugify   # type: ignore
from decimal import Decimal

# --- MASTER DATA PENGGUNA ---

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

# --- MASTER DATA VARIASI (UKURAN & WARNA) ---

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, help_text="Contoh: #7A0E1A (Merah AF)")

    def __str__(self):
        return self.name

class Size(models.Model):
    name = models.CharField(max_length=10, unique=True) # S, M, L, XL, XXL

    def __str__(self):
        return self.name

# --- PRODUK POLOS & KATEGORI ---

class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Harga dasar produk polos")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.PROTECT)
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    stock = models.PositiveIntegerField(default=0)
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('product', 'color', 'size')

    # --- TAMBAHKAN INI (Hati-hati indentasi/tab-nya) ---
    def get_price(self):
        if self.price_override:
            return self.price_override
        return self.product.price

    def __str__(self):
        return f"{self.product.name} - {self.color} - {self.size}"

# --- SISTEM CUSTOM PRODUCT (SABLON/BORDIR) ---

class CustomService(models.Model):
    name = models.CharField(max_length=100) # Contoh: 'DTF A3', 'Bordir Logo'
    service_type = models.CharField(max_length=20, choices=[('SABLON', 'Sablon'), ('BORDIR', 'Bordir')])
    additional_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} (+ Rp {self.additional_price})"

class CustomProduct(models.Model):
    """Produk paket kustom (Baju + Jasa)"""
    base_product = models.ForeignKey(Product, on_delete=models.CASCADE, help_text="Produk polos yang digunakan sebagai bahan")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    available_services = models.ManyToManyField(CustomService, related_name='custom_products')
    image = models.ImageField(upload_to='custom_products/')
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class CustomProductVariant(models.Model):
    """
    KUNCI SOLUSI: Menentukan harga baju kustom per ukuran 
    dan stok terpisah khusus untuk jalur kustom.
    """
    custom_product = models.ForeignKey(CustomProduct, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Harga baju khusus ukuran ini untuk paket kustom")
    stock = models.PositiveIntegerField(default=0, help_text="Stok khusus untuk jalur kustom")

    class Meta:
        unique_together = ('custom_product', 'size')

    def __str__(self):
        return f"{self.custom_product.name} - {self.size.name} (Stok: {self.stock})"

# --- TRANSAKSI (ORDER & PAYMENT) ---

class Order(models.Model):
    SHIPPING_STATUS_CHOICES = [
        ('PENDING', 'Menunggu Pembayaran'),
        ('PAID', 'Sudah Dibayar'),
        ('PROCESSING', 'Diproses'),
        ('SHIPPED', 'Dikirim'),
        ('COMPLETED', 'Selesai'),
        ('CANCELLED', 'Dibatalkan'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders')
    
    # PERBAIKAN DI SINI: Ganti STATUS_CHOICES menjadi SHIPPING_STATUS_CHOICES
    status = models.CharField(
        max_length=20, 
        choices=SHIPPING_STATUS_CHOICES, 
        default='PENDING'
    )

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders')
    # Sesuaikan referensi choices di sini
    status = models.CharField(max_length=20, choices=SHIPPING_STATUS_CHOICES, default='PENDING')

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=SHIPPING_STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    shipping_name = models.CharField(max_length=200)
    shipping_phone = models.CharField(max_length=20)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_province = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=10)

    courier_code = models.CharField(max_length=50)
    courier_service = models.CharField(max_length=100)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    def __str__(self):
        return f"Order #{self.id} - {self.customer}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    
    # Harga Baju (Price from CustomProductVariant)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    variant_label = models.CharField(max_length=200, blank=True, null=True)

    # --- Data Custom ---
    is_custom = models.BooleanField(default=False)
    custom_service_name = models.CharField(max_length=100, blank=True, null=True)
    custom_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0')) # Harga jasa saat transaksi
    custom_image = models.ImageField(upload_to='orders/custom_designs/%Y/%m/%d/', blank=True, null=True)
    custom_notes = models.TextField(blank=True, null=True)

    @property
    def line_total(self):
        return (self.unit_price + self.custom_price) * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

# --- KERANJANG BELANJA ---

class CartItem(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    # KUNCI SINKRONISASI: Relasi ke Varian Custom
    custom_variant = models.ForeignKey(CustomProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Relasi ke Varian Polos (Tetap ada untuk produk retail biasa)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.PositiveIntegerField(default=1)
    is_custom = models.BooleanField(default=False)
    custom_service = models.ForeignKey(CustomService, on_delete=models.SET_NULL, null=True, blank=True)
    custom_image = models.ImageField(upload_to='temp/custom_designs/', blank=True, null=True)
    custom_notes = models.TextField(blank=True, null=True)
    
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer} - {self.product.name}"