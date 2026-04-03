from django.db import models  # type: ignore
from django.contrib.auth.models import User # type: ignore
from django.utils.text import slugify # type: ignore
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

# --- PRODUK & KATEGORI ---

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
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    # Stock di sini bisa jadi stok global atau default jika tidak ada varian
    base_stock = models.PositiveIntegerField(default=0, verbose_name="Stok Dasar")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def total_stock(self):
        """Menjumlahkan semua stok dari varian yang ada"""
        if self.variants.exists():
            return sum(variant.stock for variant in self.variants.all())
        return self.base_stock

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    """Logika stok untuk Produk Polos (Warna + Ukuran)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.PROTECT)
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    stock = models.PositiveIntegerField(default=0)
    # Jika ukuran besar lebih mahal, gunakan price_override
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('product', 'color', 'size')

    def get_price(self):
        return self.price_override if self.price_override else self.product.price

    def __str__(self):
        return f"{self.product.name} - {self.color} - {self.size} (Stok: {self.stock})"

# --- TRANSAKSI (ORDER & PAYMENT) ---

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Menunggu Pembayaran'),
        ('PAID', 'Sudah Dibayar'),
        ('PROCESSING', 'Diproses'),
        ('SHIPPED', 'Dikirim'),
        ('COMPLETED', 'Selesai'),
        ('CANCELLED', 'Dibatalkan'),
    ]

    SHIPPING_STATUS_CHOICES = [
        ('NONE', 'Belum Dikirim'),
        ('ON_PROCESS', 'Diproses Gudang'),
        ('ON_DELIVERY', 'Dalam Pengiriman'),
        ('DELIVERED', 'Terkirim'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # data pengiriman
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

    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipping_status = models.CharField(max_length=20, choices=SHIPPING_STATUS_CHOICES, default='NONE')

    def __str__(self):
        return f"Order #{self.id} - {self.customer}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    # Mencatat varian spesifik yang dibeli
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    # Backup teks varian jika data varian diubah/dihapus di masa depan
    variant_label = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} ({self.variant_label}) x {self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

class Payment(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed'), ('EXPIRED', 'Expired')]
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    invoice_id = models.CharField(max_length=100, blank=True, null=True)
    payment_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Payment for Order #{self.order_id} - {self.status}"

# --- KERANJANG BELANJA ---

class CartItem(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # Menampung varian pilihan (Warna/Ukuran) di keranjang
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # User bisa punya produk yang sama di keranjang, asalkan warnanya/ukurannya berbeda
        unique_together = ('customer', 'product', 'variant')

    def __str__(self):
        variant_txt = f" [{self.variant.color}/{self.variant.size}]" if self.variant else ""
        return f"{self.customer} - {self.product.name}{variant_txt} ({self.quantity})"