from django.shortcuts import render, get_object_or_404, redirect # type: ignore
from django.contrib.auth.decorators import login_required       # type: ignore
from django.contrib import messages # type: ignore
from decimal import Decimal
from django.views.decorators.http import require_http_methods # type: ignore
from django.utils import timezone # type: ignore
from django.contrib.auth import login as auth_login # type: ignore
from django.contrib.auth import logout as auth_logout # type: ignore
from django.contrib.admin.views.decorators import staff_member_required # type: ignore
from django.db.models import Sum, Count # type: ignore
from django.utils.dateparse import parse_date # type: ignore
from django.http import HttpResponse # type: ignore
from django.utils.html import strip_tags # type: ignore
from django.core.mail import send_mail # type: ignore
from django.template.loader import render_to_string # type: ignore
from .models import CustomProduct, ProductVariant # type: ignore
from django.db.models import Sum # type: ignore
import csv
import json
from .models import (
    Product, ProductCategory, CartItem, Customer, CustomProductVariant,
    Order, OrderItem, Payment, ProductVariant, Color, Size,CustomProduct, CustomService 
)
from .forms import ProfileForm, RegisterForm

# =====================
# HOME
# =====================
def home(request):
    category_slug = request.GET.get('category')
    categories = ProductCategory.objects.all().order_by('name')
    products_qs = Product.objects.filter(is_active=True)
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(ProductCategory, slug=category_slug)
        products_qs = products_qs.filter(category=selected_category)

    products = products_qs.order_by('-created_at')[:9]

    category_cards = []
    for cat in categories:
        sample = (
            Product.objects
            .filter(is_active=True, category=cat)
            .order_by('-created_at')
            .first()
        )
        category_cards.append({
            "category": cat,
            "sample": sample,
        })

    return render(request, 'shop/home.html', {
        'products': products,
        'categories': categories,
        'category_cards': category_cards,
        'selected_category': selected_category,
    })

# =====================
# MANAGEMENT DASHBOARD (ADMIN)
# =====================

@staff_member_required
def management_dashboard(request):
    total_orders = Order.objects.count()
    total_revenue = (
        Order.objects.filter(status__in=["PAID", "COMPLETED"])
        .aggregate(total=Sum("total"))["total"] or 0
    )
    by_status = Order.objects.values("status").annotate(count=Count("id"))
    recent_orders = (
        Order.objects.select_related("customer", "customer__user")
        .order_by("-created_at")[:5]
    )

    return render(request, "shop/management_dashboard.html", {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "by_status": by_status,
        "status_choices": dict(Order.SHIPPING_STATUS_CHOICES),
        "recent_orders": recent_orders,
    })

@staff_member_required
def management_order_list(request):
    status = request.GET.get("status")
    orders = Order.objects.select_related("customer", "customer__user")\
                        .prefetch_related("items")\
                        .order_by("-created_at")
    
    if status:
        orders = orders.filter(status=status)

    return render(request, "shop/management_order_list.html", {
        "orders": orders,
        "status_filter": status,
        "order_status_choices": Order.SHIPPING_STATUS_CHOICES,
        "shipping_status_choices": Order.SHIPPING_STATUS_CHOICES,
    })

@staff_member_required
def management_order_detail(request, order_id):
    # Ambil order tanpa filter customer (karena ini akses admin)
    order = get_object_or_404(Order, id=order_id)
    # Ambil semua item beserta produknya
    items = order.items.select_related('product').all()
    
    return render(request, "shop/management_order_detail.html", {
        "order": order,
        "items": items,
        "shipping_status_choices": Order.SHIPPING_STATUS_CHOICES,
    })

@staff_member_required
@require_http_methods(["GET", "POST"])
def management_order_update(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.select_related("product", "variant").all()

    if request.method == "POST":
        new_status = request.POST.get("status")
        tracking_number = request.POST.get("tracking_number")
        shipping_status = request.POST.get("shipping_status")

        if new_status in dict(Order.SHIPPING_STATUS_CHOICES):
            order.status = new_status
        if shipping_status in dict(Order.SHIPPING_STATUS_CHOICES):
            order.shipping_status = shipping_status

        order.tracking_number = tracking_number
        order.save()
        messages.success(request, "Pesanan berhasil diperbarui.")
        return redirect("shop:management_order_list")

    return render(request, "shop/management_order_update.html", {
        "order": order,
        "items": items,
        "order_status_choices": Order.STATUS_CHOICES,
        "shipping_status_choices": Order.SHIPPING_STATUS_CHOICES,
    })

# =====================
# PRODUCT LIST & DETAIL
# =====================

def product_list(request):
    products = Product.objects.filter(is_active=True).order_by("-created_at")
    return render(request, "shop/product_list.html", {"products": products})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Ambil semua varian dari produk ini
    variants = product.variants.all()
    
    # 1. Ambil Warna yang unik dari varian yang ada
    # Kita ambil objek Color-nya langsung agar hex_code bisa terbaca di template
    color_ids = variants.values_list('color_id', flat=True).distinct()
    available_colors = Color.objects.filter(id__in=color_ids)

    # 2. Ambil Ukuran yang unik dari varian yang ada
    size_ids = variants.values_list('size_id', flat=True).distinct()
    available_sizes = Size.objects.filter(id__in=size_ids)

    # 3. Buat data JSON untuk JavaScript (Sangat Penting untuk Harga & Stok)
    variants_data = []
    for v in variants:
        variants_data.append({
            'id': v.id,
            'color_id': v.color.id,
            'size_id': v.size.id,
            'stock': v.stock,
            # KUNCI PERBAIKAN: Gunakan method get_price() agar selalu ada angka harganya
            'price': float(v.get_price()) 
        })

    context = {
        'product': product,
        'available_colors': available_colors,
        'available_sizes': available_sizes,
        'variants_json': variants_data, # Dikirim ke script di template
        'variants': variants,
    }
    return render(request, 'shop/product_detail.html', context)



# =====================
# CUSTOMER HELPER
# =====================

def get_customer(request):
    customer, created = Customer.objects.get_or_create(user=request.user)
    return customer

# =====================
# CART (DENGAN LOGIKA VARIAN)
# =====================

@login_required
def cart_detail(request):
    customer = get_customer(request)
    items = CartItem.objects.filter(customer=customer).select_related(
        'product', 'variant', 'custom_variant', 'custom_service'
    )
    
    total = Decimal('0')
    for item in items:
        if item.is_custom and item.custom_variant:
            # Harga Paket Kustom = Harga Baju Kustom + Harga Jasa
            price_baju = item.custom_variant.price
            price_jasa = item.custom_service.additional_price if item.custom_service else 0
            item.unit_total = price_baju + price_jasa
        else:
            # Harga Retail Biasa
            item.unit_total = item.variant.price_override if item.variant and item.variant.price_override else item.product.price
        
        item.line_total = item.unit_total * item.quantity
        total += item.line_total

    return render(request, "shop/cart_detail.html", {
        "items": items,
        "total": total,
    })

@login_required
@require_http_methods(["POST"])
def cart_add(request, product_id):
    customer = get_customer(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Ambil data dari Form
    size_id = request.POST.get('size')
    quantity = int(request.POST.get('quantity', 1))
    is_custom = request.POST.get('is_custom') == 'True'
    service_id = request.POST.get('custom_service')
    
    # Validasi Dasar
    if not size_id:
        messages.error(request, "Silakan pilih ukuran terlebih dahulu.")
        return redirect(request.META.get('HTTP_REFERER', 'shop:product_list'))

    if is_custom:
        # 1. Validasi Jasa
        if not service_id:
            messages.error(request, "Silakan pilih jenis jasa custom.")
            return redirect(request.META.get('HTTP_REFERER'))

        # 2. Cari Varian Kustom (Mencari Harga & Stok dari tabel CustomProductVariant)
        # Gunakan .filter().first() untuk menghindari error MultipleObjectsReturned
        custom_variant = CustomProductVariant.objects.filter(
            custom_product__base_product=product, 
            size_id=size_id
        ).first()
        
        if not custom_variant:
            messages.error(request, "Maaf, varian ukuran kustom tidak ditemukan di sistem.")
            return redirect(request.META.get('HTTP_REFERER'))

        # 3. Ambil Objek Jasa
        service = get_object_or_404(CustomService, id=service_id)
        
        # 4. Buat Item Keranjang Baru
        # (Selalu create baru untuk custom karena setiap pesanan bisa beda desain/catatan)
        CartItem.objects.create(
            customer=customer,
            product=product,
            custom_variant=custom_variant, # Penting: simpan referensi varian kustom
            quantity=quantity,
            is_custom=True,
            custom_service=service,
            custom_image=request.FILES.get('custom_image'),
            custom_notes=request.POST.get('custom_notes', '')
        )
        
    else:
        # LOGIKA PRODUK POLOS BIASA
        color_id = request.POST.get('color')
        if not color_id:
            messages.error(request, "Silakan pilih warna untuk produk polos.")
            return redirect(request.META.get('HTTP_REFERER'))
            
        variant = ProductVariant.objects.filter(
            product=product, 
            size_id=size_id, 
            color_id=color_id
        ).first()
        
        if not variant:
            messages.error(request, "Varian stok tidak tersedia.")
            return redirect(request.META.get('HTTP_REFERER'))
        
        # Untuk produk polos, kita gunakan get_or_create (update quantity jika produk sama)
        item, created = CartItem.objects.get_or_create(
            customer=customer, 
            product=product, 
            variant=variant, 
            is_custom=False,
            defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()

    messages.success(request, f"{product.name} berhasil ditambahkan ke keranjang.")
    return redirect("shop:cart_detail")

@login_required
def cart_remove(request, item_id):
    customer = get_customer(request)
    item = get_object_or_404(CartItem, id=item_id, customer=customer)
    item.delete()
    return redirect("shop:cart_detail")

# =====================
# CHECKOUT (POTONG STOK VARIAN)
# =====================

@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    customer = get_customer(request)
    # Ambil item keranjang beserta data custom & variannya secara lengkap
    cart_items = CartItem.objects.filter(customer=customer).select_related(
        'product', 'variant', 'variant__color', 'variant__size', 
        'custom_variant', 'custom_variant__size', 'custom_service'
    )

    if not cart_items.exists():
        messages.warning(request, "Keranjang Anda kosong.")
        return redirect("shop:cart_detail")

    # --- KONFIGURASI BIAYA ---
    shipping_cost = Decimal("20000") # Flat rate ongkir (Sesuaikan jika perlu)

    if request.method == "POST":
        subtotal = Decimal("0")

        # 1. Buat Header Order
        order = Order.objects.create(
            customer=customer,
            shipping_name=request.POST.get("shipping_name"),
            shipping_phone=request.POST.get("shipping_phone"),
            shipping_address=request.POST.get("shipping_address"),
            shipping_city=request.POST.get("shipping_city"),
            shipping_province=request.POST.get("shipping_province"),
            shipping_postal_code=request.POST.get("shipping_postal_code"),
            courier_code=request.POST.get("courier_code"),
            courier_service=request.POST.get("courier_service"),
            shipping_cost=shipping_cost,
        )

        # 2. Iterasi Barang di Keranjang untuk simpan permanen ke OrderItem
        for item in cart_items:
            # Tentukan Harga & Label berdasarkan jenis produk (Custom vs Retail)
            if item.is_custom and item.custom_variant:
                base_unit_price = item.custom_variant.price
                service_price = item.custom_service.additional_price if item.custom_service else Decimal("0")
                label = f"Custom: {item.custom_variant.size.name}"
                if item.custom_service:
                    label += f" ({item.custom_service.name})"
            else:
                base_unit_price = item.variant.price_override if item.variant and item.variant.price_override else item.product.price
                service_price = Decimal("0")
                label = f"{item.variant.color.name} - {item.variant.size.name}" if item.variant else "Standard"

            # 3. Simpan ke OrderItem (History Transaksi)
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=base_unit_price,        
                custom_price=service_price,       
                is_custom=item.is_custom,
                custom_service_name=item.custom_service.name if item.is_custom and item.custom_service else None,
                custom_image=item.custom_image,   
                custom_notes=item.custom_notes,   
                variant_label=label               
            )

            # Akumulasi Subtotal
            subtotal += (base_unit_price + service_price) * item.quantity

            # 4. Potong Stok Fisik
            if item.is_custom and item.custom_variant:
                item.custom_variant.stock -= item.quantity
                item.custom_variant.save()
            elif item.variant:
                item.variant.stock -= item.quantity
                item.variant.save()

        # 5. Finalisasi Header Order
        order.subtotal = subtotal
        order.total = subtotal + shipping_cost
        order.save()

        # 6. Buat Record Pembayaran
        Payment.objects.create(order=order, amount=order.total, status="PENDING")
        
        # 7. Bersihkan Keranjang
        cart_items.delete()

        messages.success(request, "Pesanan berhasil dibuat. Silakan lakukan pembayaran.")
        return redirect("shop:order_detail", order_id=order.id)

    # --- LOGIKA HARGA UNTUK TAMPILAN TEMPLATE (GET METHOD) ---
    grand_total = Decimal("0")
    for item in cart_items:
        # Kalkulasi harga yang sama dengan logic POST di atas agar sinkron
        if item.is_custom and item.custom_variant:
            price_baju = item.custom_variant.price
            price_jasa = item.custom_service.additional_price if item.custom_service else Decimal("0")
        else:
            price_baju = item.variant.price_override if item.variant and item.variant.price_override else item.product.price
            price_jasa = Decimal("0")
        
        # Simpan ke objek item secara temporer untuk ditampilkan di HTML
        item.unit_total = price_baju + price_jasa
        item.line_total = item.unit_total * item.quantity
        grand_total += item.line_total

    context = {
        "customer": customer,
        "items": cart_items,
        "subtotal": grand_total,
        "shipping_cost": shipping_cost,
        "total": grand_total + shipping_cost,
    }

    return render(request, "shop/checkout.html", context)

def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Kirim email konfirmasi pesanan baru
    subject = f'Konfirmasi Pesanan #{order.id} - AF Promotion'
    context = {'order': order, 'user': order.customer.user}
    html_message = render_to_string('emails/order_created.html', context)
    
    send_mail(
        subject, 
        strip_tags(html_message), 
        'AF Promotion <afpromotion9000@gmail.com>', 
        [order.customer.user.email], 
        html_message=html_message
    )

# =====================
# ORDER & PAYMENT (USER)
# =====================

@login_required
def order_detail(request, order_id):
    customer = get_customer(request)
    # Ambil order milik customer
    order = get_object_or_404(Order, id=order_id, customer=customer)
    
    # PERBAIKAN: Hapus "variant" dari select_related karena field tersebut 
    # sudah digantikan oleh variant_label (CharField) di model OrderItem
    items = order.items.select_related("product").all()
    
    context = {
        "order": order,
        "items": items
    }
    return render(request, "shop/order_detail.html", context)

@login_required
def order_history(request):
    customer = get_customer(request)
    orders = Order.objects.filter(customer=customer).order_by("-created_at")
    return render(request, "shop/order_history.html", {"orders": orders})

@login_required
def order_pay(request, order_id):
    customer = get_customer(request)
    order = get_object_or_404(Order, id=order_id, customer=customer)
    payment = order.payment
    payment.status = "PAID"
    payment.paid_at = timezone.now()
    payment.save()
    order.status = "PAID"
    order.save()
    return redirect("shop:order_detail", order_id=order.id)

# =====================
# PROFILE & AUTH
# =====================

@login_required
def profile(request):
    customer = get_customer(request)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            request.user.email = request.POST.get("email", "")
            request.user.save()
            messages.success(request, "Profil berhasil diperbarui.")
            return redirect("shop:profile")
    else:
        form = ProfileForm(instance=customer)
    orders = Order.objects.filter(customer=customer).order_by("-created_at")
    return render(request, "shop/profile.html", {"form": form, "orders": orders, "user_obj": request.user})

def register(request):
    if request.user.is_authenticated:
        return redirect("shop:product_list")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Customer.objects.create(user=user)
            auth_login(request, user)
            messages.success(request, "Registrasi berhasil!")
            return redirect("shop:product_list")
    else:
        form = RegisterForm()
    return render(request, "shop/register.html", {"form": form})

def logout_view(request):
    auth_logout(request)
    return redirect("login")

# =====================
# SALES REPORT (ADMIN)
# =====================

@staff_member_required
def management_sales_report(request):
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    orders = Order.objects.all().order_by("-created_at")

    if start_date:
        orders = orders.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        orders = orders.filter(created_at__date__lte=parse_date(end_date))

    total_orders = orders.count()
    total_revenue = orders.filter(status__in=["PAID", "COMPLETED"]).aggregate(total=Sum("total"))["total"] or 0
    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0
    top_products = OrderItem.objects.filter(order__in=orders).values("product__name").annotate(qty=Sum("quantity")).order_by("-qty")[:5]

    return render(request, "shop/management_sales_report.html", {
        "orders": orders,
        "start": start_date,
        "end": end_date,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
        "top_products": top_products,
        "status_choices": dict(Order.SHIPPING_STATUS_CHOICES),
    })

@staff_member_required
def management_sales_report_export(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    
    orders = Order.objects.all().order_by("-created_at")

    # Validasi: Pastikan start dan end bukan None, bukan string kosong, dan bukan teks "None"
    if start and end and start != "None" and end != "None":
        parsed_start = parse_date(start)
        parsed_end = parse_date(end)
        
        # Hanya lakukan filter jika hasil parsing tanggal berhasil (bukan None)
        if parsed_start and parsed_end:
            orders = orders.filter(
                created_at__date__gte=parsed_start, 
                created_at__date__lte=parsed_end
            )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'
    
    writer = csv.writer(response)
    # Header CSV
    writer.writerow(["Order ID", "Tanggal", "Customer", "Status", "Total"])
    
    for order in orders:
        # Gunakan get_status_display() agar status yang muncul adalah teks manusia (Menunggu Pembayaran, dll)
        # bukan kode database (PENDING, PAID)
        writer.writerow([
            order.id, 
            order.created_at.strftime("%Y-%m-%d %H:%M"), 
            order.customer.user.username, 
            order.get_status_display(), 
            float(order.total)
        ])
        
    return response

def kirim_email_status_pesanan(order):
    subject = f'Pesanan #{order.id} AF Promotion - Sedang Dikerjakan'
    
    # KOREKSI DISINI: Gunakan 'order.customer' bukan 'order.user'
    # Dan ambil user-nya dari customer
    context = {
        'order': order,
        'customer': order.customer,
        'user': order.customer.user, # Ini cara ambil user dari model Customer
    }
    
    html_message = render_to_string('emails/order_processing.html', context)
    plain_message = strip_tags(html_message)
    
    from_email = 'AF Promotion <afpromotion9000@gmail.com>'
    
    # KOREKSI DISINI: Ambil email dari customer.user
    to_email = [order.customer.user.email]

    send_mail(subject, plain_message, from_email, to_email, html_message=html_message) 

# =====================
# CUSTOM PRODUCT VIEWS
# =====================

def custom_katalog(request):
    products = CustomProduct.objects.filter(is_active=True)
    return render(request, 'shop/custom_katalog.html', {'products': products})

def custom_product_detail(request, slug):
    # 1. Ambil Produk Custom
    custom_product = get_object_or_404(CustomProduct, slug=slug, is_active=True)
    
    # 2. Ambil Varian Khusus Kustom (Harga & Stok per ukuran yang baru diisi di admin)
    custom_variants = custom_product.variants.all().select_related('size')
    
    # 3. Ambil Jasa Sablon/Bordir
    services = custom_product.available_services.all()

    # 4. Susun data untuk JavaScript (Sangat Penting untuk Harga & Stok)
    variants_list = []
    for v in custom_variants:
        variants_list.append({
            'size_id': v.size.id,
            'stock': v.stock,
            'price': float(v.price) # Harga baju kustom per ukuran (misal 3XL = 65rb)
        })

    context = {
        'custom_product': custom_product,
        'base_product': custom_product.base_product,
        'available_sizes': custom_variants, # Menggunakan varian kustom
        'services': services,
        'variants_json': json.dumps(variants_list),
    }
    return render(request, 'shop/custom_product_detail.html', context)