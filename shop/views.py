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
import csv
from .models import (
    Product, ProductCategory, CartItem, Customer, 
    Order, OrderItem, Payment, ProductVariant, Color, Size
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
        "status_choices": dict(Order.STATUS_CHOICES),
        "recent_orders": recent_orders,
    })

@staff_member_required
def management_order_list(request):
    status = request.GET.get("status")
    orders = Order.objects.select_related("customer", "customer__user").order_by("-created_at")
    if status:
        orders = orders.filter(status=status)

    return render(request, "shop/management_order_list.html", {
        "orders": orders,
        "status_filter": status,
        "order_status_choices": Order.STATUS_CHOICES,
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

        if new_status in dict(Order.STATUS_CHOICES):
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
    variants = product.variants.filter(stock__gt=0)
    
    # Siapkan data JSON untuk JavaScript agar VS Code tidak error
    variants_json = list(variants.values('color_id', 'size_id', 'stock'))
    
    available_colors = Color.objects.filter(productvariant__product=product, productvariant__stock__gt=0).distinct()
    available_sizes = Size.objects.filter(productvariant__product=product, productvariant__stock__gt=0).distinct()

    return render(request, "shop/product_detail.html", {
        "product": product,
        "variants": variants,
        "variants_json": variants_json, # Tambahkan ini
        "available_colors": available_colors,
        "available_sizes": available_sizes,
    })

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
    items = CartItem.objects.filter(customer=customer).select_related('product', 'variant')
    
    # Hitung total dengan mempertimbangkan price_override pada varian
    total = 0
    for item in items:
        price = item.variant.price_override if item.variant and item.variant.price_override else item.product.price
        total += price * item.quantity

    return render(request, "shop/cart_detail.html", {
        "items": items,
        "total": total,
    })

@login_required
@require_http_methods(["POST"])
def cart_add(request, product_id):
    customer = get_customer(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    color_id = request.POST.get('color')
    size_id = request.POST.get('size')
    quantity = int(request.POST.get('quantity', 1))

    # Wajib memilih warna dan ukuran untuk produk polos
    if not color_id or not size_id:
        messages.error(request, "Silakan pilih warna dan ukuran terlebih dahulu.")
        return redirect("shop:product_detail", slug=product.slug)

    variant = get_object_or_404(ProductVariant, product=product, color_id=color_id, size_id=size_id)

    if variant.stock < quantity:
        messages.error(request, f"Stok tidak mencukupi. Tersisa {variant.stock} pcs.")
        return redirect("shop:product_detail", slug=product.slug)

    item, created = CartItem.objects.get_or_create(
        customer=customer,
        product=product,
        variant=variant,
        defaults={"quantity": quantity},
    )

    if not created:
        item.quantity += quantity
        item.save()

    messages.success(request, f"{product.name} ({variant.color.name} - {variant.size.name}) ditambahkan ke keranjang.")
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
    cart_items = CartItem.objects.filter(customer=customer).select_related('product', 'variant')

    if not cart_items.exists():
        return redirect("shop:cart_detail")

    if request.method == "POST":
        shipping_cost = Decimal("20000") # Contoh flat rate
        subtotal = Decimal("0")

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

        for item in cart_items:
            # Gunakan harga varian jika ada
            price = item.variant.price_override if item.variant and item.variant.price_override else item.product.price
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                unit_price=price,
                variant_label=f"{item.variant.color.name} - {item.variant.size.name}" if item.variant else ""
            )
            subtotal += price * item.quantity

            # POTONG STOK VARIAN
            if item.variant:
                item.variant.stock -= item.quantity
                item.variant.save()

        order.subtotal = subtotal
        order.total = subtotal + shipping_cost
        order.save()

        Payment.objects.create(order=order, amount=order.total, status="PENDING")
        cart_items.delete()

        return redirect("shop:order_detail", order_id=order.id)

    return render(request, "shop/checkout.html", {"customer": customer, "items": cart_items})

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
    order = get_object_or_404(Order, id=order_id, customer=customer)
    items = order.items.select_related("product", "variant").all()
    return render(request, "shop/order_detail.html", {"order": order, "items": items})

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
        "status_choices": dict(Order.STATUS_CHOICES),
    })

@staff_member_required
def management_sales_report_export(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    orders = Order.objects.all().order_by("-created_at")
    if start and end:
        orders = orders.filter(created_at__date__gte=parse_date(start), created_at__date__lte=parse_date(end))

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order ID", "Tanggal", "Customer", "Status", "Total"])
    for order in orders:
        writer.writerow([order.id, order.created_at.strftime("%Y-%m-%d"), order.customer.user.username, order.status, order.total])
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