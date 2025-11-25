from django.shortcuts import render, get_object_or_404, redirect  # type: ignore
from django.contrib.auth.decorators import login_required  # type: ignore
from django.contrib import messages  # type: ignore
from decimal import Decimal
from django.views.decorators.http import require_http_methods  # type: ignore
from django.utils import timezone  # type: ignore
from django.contrib.auth import login as auth_login  # type: ignore
from django.contrib.auth import logout as auth_logout  # type: ignore
from django.contrib.admin.views.decorators import staff_member_required  # type: ignore
from django.db.models import Sum, Count  # type: ignore
from django.utils.dateparse import parse_date  # type: ignore
from django.http import HttpResponse  # type: ignore
import csv

from .forms import ProfileForm, RegisterForm
from .models import (
    Product,
    CartItem,
    Customer,
    Order,
    OrderItem,
    Payment,
)


# =====================
# HOME
# =====================

def home(request):
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'shop/home.html', {
        'products': products,
    })


# =====================
# MANAGEMENT DASHBOARD
# =====================

@staff_member_required
def management_dashboard(request):
    total_orders = Order.objects.count()

    total_revenue = (
        Order.objects.filter(status__in=["PAID", "COMPLETED"])
        .aggregate(total=Sum("total"))["total"]
        or 0
    )

    by_status = Order.objects.values("status").annotate(count=Count("id"))

    recent_orders = (
        Order.objects.select_related("customer", "customer__user")
        .order_by("-created_at")[:5]
    )

    return render(
        request,
        "shop/management_dashboard.html",
        {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "by_status": by_status,
            "status_choices": dict(Order.STATUS_CHOICES),
            "recent_orders": recent_orders,
        },
    )


@staff_member_required
def management_order_list(request):
    status = request.GET.get("status")
    orders = (
        Order.objects.select_related("customer", "customer__user")
        .order_by("-created_at")
    )

    if status:
        orders = orders.filter(status=status)

    return render(
        request,
        "shop/management_order_list.html",
        {
            "orders": orders,
            "status_filter": status,
            "order_status_choices": Order.STATUS_CHOICES,
            "shipping_status_choices": Order.SHIPPING_STATUS_CHOICES,
        },
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def management_order_update(request, order_id):
    """
    Halaman detail + update pesanan untuk admin.
    - GET  -> tampilkan detail + form status / resi
    - POST -> update status / shipping_status / tracking_number
    """
    # FILTER KE DATABASE: admin bisa akses semua order berdasarkan ID
    order = get_object_or_404(Order, id=order_id)
    items = order.items.select_related("product").all()

    if request.method == "POST":
        new_status = request.POST.get("status")
        tracking_number = request.POST.get("tracking_number")
        shipping_status = request.POST.get("shipping_status")

        status_codes = [code for code, _ in Order.STATUS_CHOICES]
        shipping_codes = [code for code, _ in Order.SHIPPING_STATUS_CHOICES]

        if new_status in status_codes:
            order.status = new_status

        if shipping_status in shipping_codes:
            order.shipping_status = shipping_status

        order.tracking_number = tracking_number
        order.save()

        messages.success(request, "Pesanan berhasil diperbarui.")
        # balik lagi ke halaman yang sama biar admin lihat hasilnya
        return redirect("shop:management_order_update", order_id=order.id)

    return render(
        request,
        "shop/management_order_update.html",
        {
            "order": order,
            "items": items,
            "order_status_choices": Order.STATUS_CHOICES,
            "shipping_status_choices": Order.SHIPPING_STATUS_CHOICES,
        },
    )


# =====================
# PRODUCT LIST & DETAIL
# =====================

def product_list(request):
    products = Product.objects.filter(is_active=True).order_by("-created_at")
    return render(
        request,
        "shop/product_list.html",
        {
            "products": products,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(
        request,
        "shop/product_detail.html",
        {
            "product": product,
        },
    )


# =====================
# CUSTOMER HELPER
# =====================

def get_customer(request):
    """
    Ambil atau buat Customer yang terhubung dengan user login.
    """
    customer, created = Customer.objects.get_or_create(user=request.user)
    return customer


# =====================
# CART
# =====================

@login_required
def cart_detail(request):
    customer = get_customer(request)
    items = CartItem.objects.filter(customer=customer)
    total = sum(item.product.price * item.quantity for item in items)

    return render(
        request,
        "shop/cart_detail.html",
        {
            "items": items,
            "total": total,
        },
    )


@login_required
def cart_add(request, product_id):
    customer = get_customer(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)

    item, created = CartItem.objects.get_or_create(
        customer=customer,
        product=product,
        defaults={"quantity": 1},
    )

    if not created:
        item.quantity += 1
        item.save()

    return redirect("shop:cart_detail")


@login_required
def cart_remove(request, item_id):
    customer = get_customer(request)
    item = get_object_or_404(CartItem, id=item_id, customer=customer)
    item.delete()
    return redirect("shop:cart_detail")


# =====================
# CHECKOUT
# =====================

@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    customer = get_customer(request)
    cart_items = CartItem.objects.filter(customer=customer)

    if not cart_items.exists():
        return redirect("shop:cart_detail")

    if request.method == "POST":
        shipping_cost = Decimal("20000")

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

        subtotal = Decimal("0")

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price,
            )
            subtotal += item.product.price * item.quantity

            # Kurangi stok
            item.product.stock -= item.quantity
            item.product.save()

        order.subtotal = subtotal
        order.total = subtotal + shipping_cost
        order.save()

        # BUAT PAYMENT RECORD
        Payment.objects.create(
            order=order,
            amount=order.total,
            status="PENDING",
        )

        # Hapus Cart
        cart_items.delete()

        return redirect("shop:order_detail", order_id=order.id)

    return render(
        request,
        "shop/checkout.html",
        {
            "customer": customer,
            "items": cart_items,
        },
    )


# =====================
# ORDER (USER)
# =====================

@login_required
def order_detail(request, order_id):
    customer = get_customer(request)
    # filter: user hanya boleh lihat order milik dia sendiri
    order = get_object_or_404(Order, id=order_id, customer=customer)
    items = order.items.all()
    return render(
        request,
        "shop/order_detail.html",
        {
            "order": order,
            "items": items,
        },
    )


@login_required
def order_history(request):
    customer = get_customer(request)

    orders = Order.objects.filter(customer=customer).order_by("-created_at")

    return render(
        request,
        "shop/order_history.html",
        {
            "orders": orders,
        },
    )
@staff_member_required
def management_order_update(request, order_id):

    # Jika GET → langsung redirect (hindari error template missing)
    if request.method == "GET":
        return redirect('shop:management_order_list')

    # Jika POST → proses update
    order = get_object_or_404(Order, id=order_id)

    new_status = request.POST.get('status')
    tracking_number = request.POST.get('tracking_number')
    shipping_status = request.POST.get('shipping_status')

    status_codes = [code for code, label in Order.STATUS_CHOICES]
    shipping_codes = [code for code, label in Order.SHIPPING_STATUS_CHOICES]

    if new_status in status_codes:
        order.status = new_status

    if shipping_status in shipping_codes:
        order.shipping_status = shipping_status

    order.tracking_number = tracking_number
    order.save()

    return redirect('shop:management_order_list')



# =====================
# PAYMENT (SIMULASI)
# =====================

@login_required
def order_pay(request, order_id):
    customer = get_customer(request)
    order = get_object_or_404(Order, id=order_id, customer=customer)

    payment = order.payment  # OneToOne, related_name='payment'

    # simulasi: langsung sukses
    payment.status = "PAID"
    payment.paid_at = timezone.now()
    payment.save()

    order.status = "PAID"
    order.save()

    return redirect("shop:order_detail", order_id=order.id)


# =====================
# PROFILE
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

    return render(
        request,
        "shop/profile.html",
        {
            "form": form,
            "orders": orders,
            "user_obj": request.user,
        },
    )


# =====================
# AUTH
# =====================

def register(request):
    if request.user.is_authenticated:
        return redirect("shop:product_list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            Customer.objects.create(user=user)

            auth_login(request, user)

            messages.success(request, "Registrasi berhasil. Selamat datang!")
            return redirect("shop:product_list")
    else:
        form = RegisterForm()

    return render(
        request,
        "shop/register.html",
        {
            "form": form,
        },
    )


def logout_view(request):
    auth_logout(request)
    return redirect("login")


# =====================
# SALES REPORT
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

    total_revenue = (
        orders.filter(status__in=["PAID", "COMPLETED"])
        .aggregate(total=Sum("total"))["total"]
        or 0
    )

    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0

    top_products = (
        OrderItem.objects.filter(order__in=orders)
        .values("product__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:5]
    )

    orders_per_status = (
        orders.values("status").annotate(count=Count("id")).order_by()
    )

    return render(
        request,
        "shop/management_sales_report.html",
        {
            "orders": orders,
            "start": start_date,
            "end": end_date,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "avg_order_value": avg_order_value,
            "top_products": top_products,
            "orders_per_status": orders_per_status,
            "status_choices": dict(Order.STATUS_CHOICES),
        },
    )


@staff_member_required
def management_sales_report_export(request):
    start = request.GET.get("start")
    end = request.GET.get("end")

    orders = Order.objects.all().order_by("-created_at")

    if start and end:
        start_date = parse_date(start)
        end_date = parse_date(end)

        if start_date and end_date:
            orders = orders.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Order ID",
            "Tanggal",
            "Customer",
            "Status",
            "Subtotal",
            "Shipping",
            "Total",
        ]
    )

    for order in orders:
        writer.writerow(
            [
                order.id,
                order.created_at.strftime("%Y-%m-%d"),
                order.customer.user.get_full_name(),
                order.status,
                order.subtotal,
                order.shipping_cost,
                order.total,
            ]
        )

    return response
