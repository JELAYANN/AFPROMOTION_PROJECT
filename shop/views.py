from django.shortcuts import render, get_object_or_404, redirect # type: ignore                    
from django.contrib.auth.decorators import login_required      # type: ignore 
from django.contrib import messages# type: ignore
from decimal import Decimal
from django.db import transaction# type: ignore
from django.views.decorators.http import require_http_methods# type: ignore
from django.utils import timezone # type: ignore
from django.contrib.auth import login as auth_login# type: ignore
from django.contrib.auth import logout as auth_logout# type: ignore
from django.contrib.admin.views.decorators import staff_member_required# type: ignore
from django.db.models import Sum, Count# type: ignore
from django.utils.dateparse import parse_date# type: ignore
from django.http import HttpResponse# type: ignore
from django.utils.html import strip_tags # type: ignore
from django.core.mail import send_mail # type: ignore
from django.template.loader import render_to_string # type: ignore
from django.views.decorators.csrf import csrf_exempt # type: ignore
import requests # type: ignore
import uuid # type: ignore
import base64 # type: ignore
import urllib3 # type: ignore
import hashlib # type: ignore
import csv
import json
import midtransclient      # type: ignore
from django.conf import settings # type: ignore
from django.urls import reverse # type: ignore
from .models import (
    Product, ProductCategory, CartItem, Customer, CustomProductVariant,
    Order, OrderItem, Payment, ProductVariant, Color, Size, CustomProduct, CustomService 
)
from .forms import ProfileForm, RegisterForm
# =====================
# HELPER
# =====================
def get_customer(request):
    customer, created = Customer.objects.get_or_create(user=request.user)
    return customer
# =====================
# HOME & PRODUCT
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
        sample = Product.objects.filter(is_active=True, category=cat).order_by('-created_at').first()
        category_cards.append({"category": cat, "sample": sample})
    return render(request, 'shop/home.html', {
        'products': products, 'categories': categories,
        'category_cards': category_cards, 'selected_category': selected_category,
    })
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by("-created_at")
    return render(request, "shop/product_list.html", {"products": products})
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    variants = product.variants.all()
    available_colors = Color.objects.filter(id__in=variants.values_list('color_id', flat=True).distinct())
    available_sizes = Size.objects.filter(id__in=variants.values_list('size_id', flat=True).distinct())
    variants_data = [{
        'id': v.id, 'color_id': v.color.id, 'size_id': v.size.id,
        'stock': v.stock, 'price': float(v.get_price())
    } for v in variants]
    return render(request, 'shop/product_detail.html', {
        'product': product, 'available_colors': available_colors,
        'available_sizes': available_sizes, 'variants_json': variants_data, 'variants': variants,
    })
# =====================
# CART
# =====================
@login_required
def cart_detail(request):
    customer = get_customer(request)
    items = CartItem.objects.filter(customer=customer).select_related('product', 'variant', 'custom_variant', 'custom_service')
    total = Decimal('0')
    for item in items:
        if item.is_custom and item.custom_variant:
            item.unit_total = item.custom_variant.price + (item.custom_service.additional_price if item.custom_service else 0)
        else:
            item.unit_total = item.variant.price_override if item.variant and item.variant.price_override else item.product.price
        item.line_total = item.unit_total * item.quantity
        total += item.line_total
    return render(request, "shop/cart_detail.html", {"items": items, "total": total})
@login_required
@require_http_methods(["POST"])
def cart_add(request, product_id):
    customer = get_customer(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    size_id = request.POST.get('size')
    quantity = int(request.POST.get('quantity', 1))
    is_custom = request.POST.get('is_custom') == 'True'
    if not size_id:
        messages.error(request, "Pilih ukuran terlebih dahulu.")
        return redirect(request.META.get('HTTP_REFERER', 'shop:product_list'))
    if is_custom:
        service_id = request.POST.get('custom_service')
        if not service_id:
            messages.error(request, "Pilih jenis jasa custom.")
            return redirect(request.META.get('HTTP_REFERER'))
        
        custom_variant = CustomProductVariant.objects.filter(custom_product__base_product=product, size_id=size_id).first()
        if not custom_variant:
            messages.error(request, "Varian kustom tidak ditemukan.")
            return redirect(request.META.get('HTTP_REFERER'))
        CartItem.objects.create(
            customer=customer, product=product, custom_variant=custom_variant,
            quantity=quantity, is_custom=True, custom_service_id=service_id,
            custom_image=request.FILES.get('custom_image'), custom_notes=request.POST.get('custom_notes', '')
        )
    else:
        color_id = request.POST.get('color')
        variant = ProductVariant.objects.filter(product=product, size_id=size_id, color_id=color_id).first()
        if not variant:
            messages.error(request, "Varian tidak tersedia.")
            return redirect(request.META.get('HTTP_REFERER'))
        
        item, created = CartItem.objects.get_or_create(
            customer=customer, product=product, variant=variant, is_custom=False,
            defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()
    messages.success(request, f"{product.name} ditambah ke keranjang.")
    return redirect("shop:cart_detail")
@login_required
def cart_remove(request, item_id):
    get_object_or_404(CartItem, id=item_id, customer=get_customer(request)).delete()
    return redirect("shop:cart_detail")
# =====================
# CHECKOUT & PAYMENT
# =====================
@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    customer = get_customer(request)
    # Ambil item keranjang
    cart_items = CartItem.objects.filter(customer=customer).select_related(
        'product',
        'variant',
        'custom_variant',
        'custom_service'
    )
    # Jika keranjang kosong
    if not cart_items.exists():
        messages.warning(request, "Keranjang kosong.")
        return redirect("shop:cart_detail")
    shipping_cost = Decimal("20000")
    # =========================
    # POST / CREATE ORDER
    # =========================
    if request.method == "POST":
        try:
            with transaction.atomic():
                # =========================
                # VALIDASI STOK
                # =========================
                for item in cart_items:
                    variant_obj = item.custom_variant if item.is_custom else item.variant
                    if not variant_obj:
                        messages.error(
                            request,
                            f"Variant untuk {item.product.name} tidak ditemukan."
                        )
                        return redirect("shop:cart_detail")
                    if variant_obj.stock < item.quantity:
                        messages.error(
                            request,
                            f"Stok {item.product.name} tidak cukup."
                        )
                        return redirect("shop:cart_detail")
                # =========================
                # BUAT ORDER
                # =========================
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
                # =========================
                # PINDAHKAN CART -> ORDER ITEM
                # =========================
                for item in cart_items:
                    # =====================
                    # CUSTOM PRODUCT
                    # =====================
                    if item.is_custom and item.custom_variant:
                        unit_price = item.custom_variant.price
                        service_price = (
                            item.custom_service.additional_price
                            if item.custom_service
                            else Decimal("0")
                        )
                        variant_label = f"Custom: {item.custom_variant.size.name}"
                        # Kurangi stok
                        item.custom_variant.stock -= item.quantity
                        item.custom_variant.save()
                    # =====================
                    # STANDARD PRODUCT
                    # =====================
                    else:
                        unit_price = (
                            item.variant.price_override
                            if item.variant and item.variant.price_override
                            else item.product.price
                        )
                        service_price = Decimal("0")
                        variant_label = (
                            f"{item.variant.color.name} - {item.variant.size.name}"
                            if item.variant
                            else "Standard"
                        )
                        # Kurangi stok
                        if item.variant:
                            item.variant.stock -= item.quantity
                            item.variant.save()
                    # =====================
                    # HITUNG TOTAL ITEM
                    # =====================
                    line_total = (
                        (unit_price + service_price)
                        * item.quantity
                    )
                    subtotal += line_total
                    # =====================
                    # CREATE ORDER ITEM
                    # =====================
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        unit_price=unit_price,
                        custom_price=service_price,
                        is_custom=item.is_custom,
                        variant_label=variant_label,
                        # custom design
                        custom_image=item.custom_image if item.is_custom else None,
                        custom_notes=item.custom_notes if item.is_custom else None,
                    )
                # =========================
                # FINALISASI TOTAL ORDER
                # =========================
                order.subtotal = subtotal
                order.total = subtotal + shipping_cost
                order.save()
                # =========================
                # CREATE PAYMENT
                # =========================
                Payment.objects.create(
                    order=order,
                    amount=order.total,
                    status="PENDING"
                )
                # =========================
                # HAPUS KERANJANG
                # =========================
                cart_items.delete()
                messages.success(
                    request,
                    "Order berhasil dibuat. Lanjutkan pembayaran."
                )
                # =========================
                # REDIRECT KE MIDTRANS
                # =========================
                return redirect(
                    "shop:order_pay",
                    order_id=order.id
                )
        except Exception as e:
            print("CHECKOUT ERROR:", str(e))
            messages.error(
                request,
                f"Terjadi kesalahan checkout: {str(e)}"
            )
            return redirect("shop:checkout")
    # =========================
    # GET / TAMPILAN CHECKOUT
    # =========================
    grand_total = Decimal("0")
    for item in cart_items:
        product_price = (
            item.custom_variant.price
            if item.is_custom
            else (
                item.variant.price_override
                if item.variant and item.variant.price_override
                else item.product.price
            )
        )
        service_price = (
            item.custom_service.additional_price
            if item.is_custom and item.custom_service
            else Decimal("0")
        )
        item.line_total = (
            (product_price + service_price)
            * item.quantity
        )
        grand_total += item.line_total
    return render(request, "shop/checkout.html", {
        "customer": customer,
        "items": cart_items,
        "subtotal": grand_total,
        "shipping_cost": shipping_cost,
        "total": grand_total + shipping_cost,
    })

@login_required
def order_pay(request, order_id):
    print("ORDER PAY DIPANGGIL")
    customer = get_customer(request)
    order = get_object_or_404(
        Order,
        id=order_id,
        customer=customer
    )
    # =========================
    # CEGAH PEMBAYARAN ULANG
    # =========================
    payment = Payment.objects.filter(order=order).first()
    if payment and payment.status == "PAID":
        messages.success(
            request,
            "Pesanan ini sudah dibayar."
        )
        return redirect(
            "shop:order_detail",
            order_id=order.id
        )
    try:
        print("SERVER KEY:", settings.MIDTRANS_SERVER_KEY)
        print("IS PRODUCTION:", settings.MIDTRANS_IS_PRODUCTION)
        # =========================
        # MIDTRANS SNAP
        # =========================
        snap = midtransclient.Snap(
            is_production=settings.MIDTRANS_IS_PRODUCTION,
            server_key=settings.MIDTRANS_SERVER_KEY.strip()
        )
        # =========================
        # UNIQUE TRANSACTION ID
        # =========================
        unique_trx_id = (
            f"NEW-AF-{order.id}-{uuid.uuid4().hex[:6]}"
        )
        # =========================
        # ITEM DETAILS
        # =========================
        item_details = []
        subtotal_calculated = 0
        for item in order.items.all():
            item_price = int(
                item.unit_price + item.custom_price
            )
            line_total = (
                item_price * item.quantity
            )
            subtotal_calculated += line_total
            item_details.append({
                "id": str(item.id),
                "price": item_price,
                "quantity": item.quantity,
                "name": item.product.name[:50]
            })
        # =========================
        # SHIPPING
        # =========================
        item_details.append({
            "id": "SHIPPING",
            "price": int(order.shipping_cost),
            "quantity": 1,
            "name": "Biaya Pengiriman"
        })
        gross_amount = (
            subtotal_calculated
            + int(order.shipping_cost)
        )
        # =========================
        # FINISH URL
        # =========================
        finish_url = request.build_absolute_uri(
            reverse(
                "shop:payment_success",
                args=[order.id]
            )
        )
        print("FINISH URL:")
        print(finish_url)
        # =========================
        # TRANSACTION DATA
        # =========================
        transaction_data = {
            "transaction_details": {
                "order_id": unique_trx_id,
                "gross_amount": gross_amount
            },
            "customer_details": {
                "first_name": order.shipping_name or "Customer",
                "phone": order.shipping_phone or "",
                "email": request.user.email or "customer@mail.com",
            },
            "item_details": item_details,
            # =========================
            # CALLBACK REDIRECT
            # =========================
            "callbacks": {
                "finish": finish_url
            }
        }
        print("TRANSACTION DATA:")
        print(transaction_data)
        # =========================
        # CREATE MIDTRANS TRANSACTION
        # =========================
        transaction = snap.create_transaction(
            transaction_data
        )
        print("MIDTRANS RESPONSE:")
        print(transaction)
        # =========================
        # SNAP TOKEN
        # =========================
        snap_token = transaction.get("token")
        if not snap_token:
            raise Exception(
                "Snap token tidak ditemukan."
            )
        # =========================
        # CREATE / UPDATE PAYMENT
        # =========================
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "amount": gross_amount,
                "status": "PENDING"
            }
        )
        payment.external_id = unique_trx_id
        payment.amount = gross_amount
        payment.status = "PENDING"
        if hasattr(payment, "snap_token"):
            payment.snap_token = snap_token
        payment.save()
        # =========================
        # RENDER PAYMENT PAGE
        # =========================
        return render(
            request,
            "shop/payment_page.html",
            {
                "order": order,
                "snap_token": snap_token,
                "midtrans_client_key": settings.MIDTRANS_CLIENT_KEY.strip()
            }
        )
    except Exception as e:
        print("MIDTRANS ERROR:")
        print(str(e))
        messages.error(
            request,
            f"Midtrans Error: {str(e)}"
        )
        return redirect(
            "shop:order_detail",
            order_id=order.id
        )
    
@csrf_exempt
def midtrans_callback(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        notification = json.loads(request.body)
        print("MIDTRANS CALLBACK:")
        print(notification)
        # =========================
        # AMBIL DATA
        # =========================
        order_id_full = notification.get("order_id")
        transaction_status = notification.get("transaction_status")
        status_code = notification.get("status_code")
        gross_amount = notification.get("gross_amount")
        signature_key = notification.get("signature_key")
        # =========================
        # VALIDASI SIGNATURE
        # =========================
        server_key = settings.MIDTRANS_SERVER_KEY
        raw_signature = (
            order_id_full +
            status_code +
            gross_amount +
            server_key
        )
        generated_signature = hashlib.sha512(
            raw_signature.encode()
        ).hexdigest()
        if signature_key != generated_signature:
            print("SIGNATURE INVALID!")
            return HttpResponse(status=403)
        print("SIGNATURE VALID")
        # =========================
        # AMBIL ORDER
        # =========================
        order_id = order_id_full.split("-")[2]
        order = get_object_or_404(
            Order,
            id=order_id
        )
        payment = Payment.objects.filter(
            order=order
        ).first()
        # =========================
        # UPDATE STATUS
        # =========================
        if transaction_status in ["capture", "settlement"]:
            order.status = "PAID"
            order.save()
            if payment:
                payment.status = "PAID"
                payment.paid_at = timezone.now()
                payment.save()
            print(f"ORDER #{order.id} BERHASIL DIUPDATE KE PAID")
            send_order_update_notification(
                order,
                "PAID"
            )
        elif transaction_status in [
            "deny",
            "expire",
            "cancel"
        ]:
            order.status = "CANCELLED"
            order.save()
            if payment:
                payment.status = "FAILED"
                payment.save()
            print(f"ORDER #{order.id} DIBATALKAN")
        return HttpResponse(status=200)
    except Exception as e:
        print("CALLBACK ERROR:")
        print(str(e))
        return HttpResponse(status=500)

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        customer__user=request.user
    )
    return render(
        request,
        'shop/payment_success.html',
        {
            'order': order
        }
    )

# =====================
# ORDER HISTORY & PROFILE
# =====================
@login_required
def order_history(request):
    return render(request, "shop/order_history.html", {"orders": Order.objects.filter(customer=get_customer(request)).order_by("-created_at")})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=get_customer(request))
    return render(request, "shop/order_detail.html", {"order": order, "items": order.items.select_related("product").all()})

@login_required
def profile(request):
    customer = get_customer(request)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            u = request.user
            u.first_name, u.last_name, u.email = request.POST.get("first_name", ""), request.POST.get("last_name", ""), request.POST.get("email", "")
            u.save()
            messages.success(request, "Profil diperbarui.")
            return redirect("shop:profile")
    else: form = ProfileForm(instance=customer)
    return render(request, "shop/profile.html", {"form": form, "orders": Order.objects.filter(customer=customer).order_by("-created_at"), "user_obj": request.user})

def register(request):
    if request.user.is_authenticated: return redirect("shop:product_list")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Customer.objects.create(user=user)
            auth_login(request, user)
            messages.success(request, "Registrasi berhasil!")
            return redirect("shop:product_list")
    else: form = RegisterForm()
    return render(request, "shop/register.html", {"form": form})

def logout_view(request):
    auth_logout(request)
    return redirect("login")
# =====================
# MANAGEMENT (ADMIN)
# =====================
VALID_REVENUE_STATUSES = [
    "PAID",
    "PROCESSING",
    "SHIPPED",
    "COMPLETED"
]

@staff_member_required
def management_dashboard(request):
    revenue_orders = Order.objects.filter(
        status__in=VALID_REVENUE_STATUSES
    )
    return render(request, "shop/management_dashboard.html", {
        "total_orders": Order.objects.count(),
        "total_revenue":
            revenue_orders.aggregate(
                total=Sum("total")
            )["total"] or 0,
        "paid_orders_count":
            revenue_orders.count(),
        "pending_orders_count":
            Order.objects.filter(status="PENDING").count(),
        "cancelled_orders_count":
            Order.objects.filter(status="CANCELLED").count(),
        "by_status":
            Order.objects.values("status")
            .annotate(count=Count("id")),
        "recent_orders":
            Order.objects.select_related("customer__user")
            .order_by("-created_at")[:5],
    })

@staff_member_required
def management_order_list(request):
    # =========================
    # UPDATE STATUS
    # =========================
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        new_status = request.POST.get("status")
        if order_id and new_status:
            order = get_object_or_404(Order, id=order_id)
            old_status = order.status
            # update status
            order.status = new_status
            order.save()
            # =========================
            # NOTIFICATION LOGIC
            # =========================
            # PROCESSING
            if (
                new_status == "PROCESSING"
                and old_status != "PROCESSING"
            ):
                send_order_update_notification(
                    order,
                    "PROCESSING"
                )
                messages.success(
                    request,
                    f"Pesanan #{order.id} diproses & notifikasi dikirim!"
                )
            # SHIPPED
            elif (
                new_status == "SHIPPED"
                and old_status != "SHIPPED"
            ):
                send_order_update_notification(
                    order,
                    "SHIPPED"
                )
                messages.success(
                    request,
                    f"Pesanan #{order.id} dikirim & notifikasi dikirim!"
                )
            else:
                messages.success(
                    request,
                    f"Status pesanan #{order.id} diperbarui."
                )
            return redirect("shop:management_order_list")
    # =========================
    # FILTER LIST
    # =========================
    status_filter = request.GET.get("status")
    orders = (
        Order.objects
        .select_related("customer__user")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    if status_filter:
        orders = orders.filter(status=status_filter)
    context = {
        "orders": orders,
        "order_status_choices": Order.SHIPPING_STATUS_CHOICES,
        "status_filter": status_filter,
    }
    return render(
        request,
        "shop/management_order_list.html",
        context
    )

@staff_member_required
def management_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(
        request,
        "shop/management_order_detail.html",
        {
            "order": order,
            "items": order.items.select_related("product").all()
        }
    )

@staff_member_required
@require_http_methods(["GET", "POST"])
def management_order_update(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        order.status = request.POST.get("status")
        order.shipping_status = request.POST.get("shipping_status")
        order.tracking_number = request.POST.get("tracking_number")
        order.save()
        messages.success(
            request,
            "Update pesanan berhasil."
        )
        return redirect("shop:management_order_list")
    return render(
        request,
        "shop/management_order_update.html",
        {
            "order": order,
            "order_status_choices": Order.STATUS_CHOICES,
            "shipping_status_choices": Order.SHIPPING_STATUS_CHOICES,
        }
    )

@staff_member_required
def management_sales_report(request):
    # =========================
    # FILTER DATE
    # =========================
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    orders = Order.objects.all().order_by("-created_at")
    # START DATE
    if start_date and start_date != "None" and start_date != "":
        parsed_start = parse_date(start_date)
        if parsed_start:
            orders = orders.filter(
                created_at__date__gte=parsed_start
            )
    # END DATE
    if end_date and end_date != "None" and end_date != "":
        parsed_end = parse_date(end_date)
        if parsed_end:
            orders = orders.filter(
                created_at__date__lte=parsed_end
            )
    # =========================
    # VALID REVENUE ORDERS
    # =========================
    revenue_orders = orders.filter(
        status__in=VALID_REVENUE_STATUSES
    )
    # =========================
    # STATS
    # =========================
    total_orders = orders.count()
    total_revenue = (
        revenue_orders.aggregate(
            total=Sum("total")
        )["total"] or 0
    )
    avg_order_value = (
        total_revenue / revenue_orders.count()
        if revenue_orders.count() > 0
        else 0
    )
    # =========================
    # TOP PRODUCTS
    # =========================
    top_products = (
        OrderItem.objects
        .filter(order__in=revenue_orders)
        .values("product__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:5]
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
            "status_choices":
                dict(Order.SHIPPING_STATUS_CHOICES),
        }
    )


@staff_member_required
def management_sales_report_export(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    orders = Order.objects.all().order_by("-created_at")
    # START DATE
    if start and start != "None" and start != "":
        parsed_start = parse_date(start)
        if parsed_start:
            orders = orders.filter(
                created_at__date__gte=parsed_start
            )
    # END DATE
    if end and end != "None" and end != "":
        parsed_end = parse_date(end)
        if parsed_end:
            orders = orders.filter(
                created_at__date__lte=parsed_end
            )
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="sales_report_af_promotion.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        "Order ID",
        "Tanggal",
        "Customer",
        "Status",
        "Total"
    ])
    for order in orders:
        writer.writerow([
            order.id,
            order.created_at.strftime("%Y-%m-%d %H:%M"),
            order.customer.user.username,
            order.get_status_display(),
            float(order.total)
        ])
    return response
# =====================
# CUSTOM KATALOG
# =====================
def custom_katalog(request):
    return render(request, 'shop/custom_katalog.html', {'products': CustomProduct.objects.filter(is_active=True)})
def custom_product_detail(request, slug):
    cp = get_object_or_404(CustomProduct, slug=slug, is_active=True)
    cv = cp.variants.all().select_related('size')
    v_json = [{'size_id': v.size.id, 'stock': v.stock, 'price': float(v.price)} for v in cv]
    return render(request, 'shop/custom_product_detail.html', {
        'custom_product': cp, 'base_product': cp.base_product, 'available_sizes': cv,
        'services': cp.available_services.all(), 'variants_json': json.dumps(v_json),
    })

# =====================
# Notifikasi 
# =====================
def send_order_update_notification(order, status_type):
    try:
        templates = {
            'PAID': {
                'subject': f'Pembayaran Berhasil - Pesanan #{order.id}',
                'template': 'emails/payment_success.html',
                'wa_msg': f"Halo {order.shipping_name}, pembayaran pesanan #{order.id} sebesar Rp {order.total:,.0f} telah kami terima. Terima kasih!"
            },
            'PROCESSING': {
                'subject': f'Pesanan Diproses - Pesanan #{order.id}',
                'template': 'emails/order_processing.html',
                'wa_msg': f"Halo {order.shipping_name}, pesanan #{order.id} saat ini sedang dalam tahap produksi/packing. Kami akan menginfokan kembali saat dikirim."
            },
            'SHIPPED': {
                'subject': f'Pesanan Dikirim - Pesanan #{order.id}',
                'template': 'emails/order_shipped.html',
                'wa_msg': f"Kabar gembira {order.shipping_name}! Pesanan #{order.id} telah dikirim via {order.courier_code}. No Resi: {order.tracking_number}."
            }
        }
        data = templates.get(status_type)
        if not data: return
        # --- KIRIM EMAIL ---
        context = {'order': order, 'user': order.customer.user}
        html_message = render_to_string(data['template'], context)
        send_mail(
            data['subject'],
            strip_tags(html_message),
            settings.DEFAULT_FROM_EMAIL,
            [order.customer.user.email],
            html_message=html_message
        )
        # --- KIRIM WHATSAPP (Contoh Fonnte) ---
        requests.post(
            'https://api.fonnte.com/send',
            data={
                'target': order.shipping_phone,
                'message': data['wa_msg'],
            },
            headers={
                'Authorization': settings.FONNTE_TOKEN
            }
        )
    except Exception as e:
        print(f"Gagal mengirim notifikasi {status_type}: {e}")