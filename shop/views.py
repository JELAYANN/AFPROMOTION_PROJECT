from django.shortcuts import render, get_object_or_404, redirect # type: ignore                    
from django.contrib.auth.decorators import login_required      # type: ignore 
from django.views.decorators.http import require_POST # type: ignore
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
from django.http import JsonResponse # type: ignore
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
from .shipping import (
    get_provinces,
    get_cities,
    get_subdistricts,
    get_shipping_cost,
    create_shipment
)
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
@login_required
def checkout(request):
    customer = get_customer(request)
    cart_items = CartItem.objects.filter(
        customer=customer
    ).select_related(
        'product',
        'variant',
        'custom_variant',
        'custom_service'
    )
    # =========================
    # VALIDASI CART
    # =========================
    if not cart_items.exists():
        messages.warning(
            request,
            "Keranjang kosong."
        )
        return redirect(
            "shop:cart_detail"
        )
    # =========================
    # VALIDASI ALAMAT CUSTOMER
    # =========================
    if not customer.subdistrict_id:
        messages.warning(
            request,
            "Silakan lengkapi alamat profile terlebih dahulu."
        )
        return redirect(
            "shop:profile"
        )
    # =========================
    # HITUNG TOTAL BERAT
    # =========================
    total_weight = 0
    for item in cart_items:
        weight = getattr(
            item.product,
            'weight',
            1000
        ) or 1000
        total_weight += (
            weight * item.quantity
        )
    # =========================
    # POST / CREATE ORDER
    # =========================
    if request.method == "POST":
        try:
            raw_shipping_cost = request.POST.get(
                "shipping_cost",
                "0"
            )
            shipping_cost = Decimal(
                raw_shipping_cost.replace(',', '')
            )
        except:
            shipping_cost = Decimal("0")
        # =========================
        # VALIDASI SHIPPING
        # =========================
        courier_code = request.POST.get(
            "courier_code"
        )
        courier_service = request.POST.get(
            "courier_service"
        )
        destination_subdistrict_id = request.POST.get(
            "destination_subdistrict_id"
        )
        if not courier_code or not courier_service:
            messages.error(
                request,
                "Silakan pilih kurir pengiriman."
            )
            return redirect(
                "shop:checkout"
            )
        try:
            with transaction.atomic():
                # =========================
                # VALIDASI STOK
                # =========================
                for item in cart_items:
                    variant_obj = (
                        item.custom_variant
                        if item.is_custom
                        else item.variant
                    )
                    if not variant_obj:
                        messages.error(
                            request,
                            f"Variant {item.product.name} tidak ditemukan."
                        )
                        return redirect(
                            "shop:cart_detail"
                        )
                    if variant_obj.stock < item.quantity:
                        messages.error(
                            request,
                            f"Stok {item.product.name} tidak cukup."
                        )
                        return redirect(
                            "shop:cart_detail"
                        )
                # =========================
                # CREATE ORDER
                # =========================
                order = Order.objects.create(
                    customer=customer,
                    # SHIPPING CUSTOMER
                    shipping_name=request.POST.get(
                        "shipping_name"
                    ),
                    shipping_phone=request.POST.get(
                        "shipping_phone"
                    ),
                    shipping_address=request.POST.get(
                        "shipping_address"
                    ),
                    shipping_city=request.POST.get(
                        "shipping_city"
                    ),
                    shipping_province=request.POST.get(
                        "shipping_province"
                    ),
                    shipping_postal_code=request.POST.get(
                        "shipping_postal_code"
                    ),
                    # SHIPPING REGION
                    destination_subdistrict_id=
                    destination_subdistrict_id,
                    # COURIER
                    courier_code=courier_code,
                    courier_service=
                    courier_service,
                    # SHIPPING
                    shipping_cost=shipping_cost,
                    total_weight=total_weight,
                )
                subtotal = Decimal("0")
                # =========================
                # CART -> ORDER ITEM
                # =========================
                for item in cart_items:
                    # CUSTOM PRODUCT
                    if item.is_custom and item.custom_variant:
                        unit_price = (
                            item.custom_variant.price
                        )
                        service_price = (
                            item.custom_service.additional_price
                            if item.custom_service
                            else Decimal("0")
                        )
                        variant_label = (
                            f"Custom: "
                            f"{item.custom_variant.size.name}"
                        )
                        # REDUCE STOCK
                        item.custom_variant.stock -= (
                            item.quantity
                        )
                        item.custom_variant.save()
                    # NORMAL PRODUCT
                    else:
                        unit_price = (
                            item.variant.price_override
                            if item.variant
                            and item.variant.price_override
                            else item.product.price
                        )
                        service_price = Decimal("0")
                        variant_label = (
                            f"{item.variant.color.name}"
                            f" - "
                            f"{item.variant.size.name}"
                            if item.variant
                            else "Standard"
                        )
                        # REDUCE STOCK
                        if item.variant:
                            item.variant.stock -= (
                                item.quantity
                            )
                            item.variant.save()
                    # TOTAL
                    line_total = (
                        unit_price + service_price
                    ) * item.quantity
                    subtotal += line_total
                    # CREATE ORDER ITEM
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        unit_price=unit_price,
                        custom_price=service_price,
                        is_custom=item.is_custom,
                        variant_label=variant_label,
                        custom_image=(
                            item.custom_image
                            if item.is_custom
                            else None
                        ),
                        custom_notes=(
                            item.custom_notes
                            if item.is_custom
                            else None
                        ),
                    )
                # =========================
                # FINAL TOTAL
                # =========================
                order.subtotal = subtotal
                order.total = (
                    subtotal + shipping_cost
                )
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
                # CLEAR CART
                # =========================
                cart_items.delete()
                messages.success(
                    request,
                    "Order berhasil dibuat."
                )
                return redirect(
                    "shop:order_pay",
                    order_id=order.id
                )
        except Exception as e:
            print(
                "CHECKOUT ERROR:",
                str(e)
            )
            messages.error(
                request,
                f"Checkout gagal: {str(e)}"
            )
            return redirect(
                "shop:checkout"
            )
    # =========================
    # GET / DISPLAY CHECKOUT
    # =========================
    grand_total = Decimal("0")
    for item in cart_items:
        product_price = (
            item.custom_variant.price
            if item.is_custom
            else (
                item.variant.price_override
                if item.variant
                and item.variant.price_override
                else item.product.price
            )
        )
        service_price = (
            item.custom_service.additional_price
            if item.is_custom
            and item.custom_service
            else Decimal("0")
        )
        item.line_total = (
            product_price + service_price
        ) * item.quantity
        grand_total += item.line_total
    context = {
        "customer": customer,
        "items": cart_items,
        "subtotal": grand_total,
        "total_weight": total_weight,
        "shipping_cost": Decimal("0"),
        "total": grand_total,
    }
    return render(
        request,
        "shop/checkout.html",
        context
    )
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
        print("MIDTRANS CALLBACK:", notification)
        # =========================
        # AMBIL DATA
        # =========================
        order_id_full = notification.get("order_id")
        transaction_status = notification.get("transaction_status")
        status_code = notification.get("status_code")
        gross_amount = notification.get("gross_amount")
        signature_key = notification.get("signature_key")
        # =========================
        # VALIDASI ORDER ID
        # =========================
        if not order_id_full:
            print("ORDER ID TIDAK ADA")
            return HttpResponse(status=400)
        # =========================
        # VALIDASI SIGNATURE
        # =========================
        if status_code and gross_amount and signature_key:
            server_key = settings.MIDTRANS_SERVER_KEY.strip()
            raw_signature = (
                str(order_id_full)
                + str(status_code)
                + str(gross_amount)
                + str(server_key)
            )
            generated_signature = hashlib.sha512(
                raw_signature.encode()
            ).hexdigest()
            if signature_key != generated_signature:
                print("SIGNATURE INVALID!")
                return HttpResponse(status=403)
            print("SIGNATURE VALID")
        else:
            print("SIGNATURE SKIPPED (sandbox/local callback)")
        # =========================
        # GET ORDER
        # =========================
        order_id = order_id_full.split("-")[2]
        order = get_object_or_404(Order, id=order_id)
        payment = Payment.objects.filter(order=order).first()
        # ==================================================
        # SUCCESS PAYMENT
        # ==================================================
        if transaction_status in ["capture", "settlement"]:
            # =========================
            # PAYMENT UPDATE
            # =========================
            if payment:
                if payment.status != "PAID":
                    payment.status = "PAID"
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=["status", "paid_at"])
            # =========================
            # ORDER UPDATE
            # =========================
            if order.status != "PAID":
                order.status = "PAID"
                order.save(update_fields=["status"])
                print(f"ORDER #{order.id} PAID")
            else:
                print(f"ORDER #{order.id} already PAID")
            # ==================================================
            # CREATE SHIPMENT (ONLY ONCE)
            # ==================================================
            if not order.tracking_number:
                shipment_result = create_shipment(order)
                print("SHIPMENT RESULT:", shipment_result)
                if shipment_result.get("success"):
                    awb = shipment_result.get("awb")
                    if awb:
                        order.tracking_number = awb
                        order.shipping_status = "PROCESSING"
                        order.save(update_fields=[
                            "tracking_number",
                            "shipping_status"
                        ])
                        print(f"AWB CREATED: {awb}")
                    else:
                        print("AWB NOT FOUND")
                else:
                    print("SHIPMENT FAILED")
            else:
                print(f"ORDER #{order.id} already has AWB")
        # ==================================================
        # FAILED PAYMENT
        # ==================================================
        elif transaction_status in ["deny", "expire", "cancel"]:
            if order.status != "CANCELLED":
                order.status = "CANCELLED"
                order.save(update_fields=["status"])
            if payment:
                if payment.status != "FAILED":
                    payment.status = "FAILED"
                    payment.save(update_fields=["status"])
            print(f"ORDER #{order.id} CANCELLED")
        return HttpResponse(status=200)
    except Exception as e:
        print("CALLBACK ERROR:", str(e))
        return HttpResponse(status=500)
@login_required
def payment_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        customer__user=request.user
    )
    payment = Payment.objects.filter(order=order).first()
    context = {
        "order": order,
        "payment": payment
    }
    return render(request, 'shop/payment_success.html', context)
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
        form = ProfileForm(
            request.POST,
            instance=customer
        )
        if form.is_valid():
            customer = form.save(
                commit=False
            )
            # =========================
            # SHIPPING REGION
            # =========================
            customer.province = request.POST.get(
                "province",
                ""
            )
            customer.city = request.POST.get(
                "city",
                ""
            )
            customer.subdistrict = request.POST.get(
                "subdistrict",
                ""
            )
            # =========================
            # SHIPPING REGION ID
            # =========================
            customer.province_id = request.POST.get(
                "province_id",
                ""
            )
            customer.city_id = request.POST.get(
                "city_id",
                ""
            )
            customer.subdistrict_id = request.POST.get(
                "subdistrict_id",
                ""
            )
            customer.save()
            # =========================
            # UPDATE USER
            # =========================
            u = request.user
            u.first_name = request.POST.get(
                "first_name",
                ""
            )
            u.last_name = request.POST.get(
                "last_name",
                ""
            )
            u.email = request.POST.get(
                "email",
                ""
            )
            u.save()
            messages.success(
                request,
                "Profil berhasil diperbarui."
            )
            return redirect(
                "shop:profile"
            )
    else:
        form = ProfileForm(
            instance=customer
        )
    orders = Order.objects.filter(
        customer=customer
    ).order_by(
        "-created_at"
    )
    context = {
        "form": form,
        "orders": orders,
        "user_obj": request.user,
        "customer": customer,
    }
    return render(
        request,
        "shop/profile.html",
        context
    )
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
        order_id = request.POST.get(
            "order_id"
        )
        new_status = request.POST.get(
            "status"
        )
        if order_id and new_status:
            order = get_object_or_404(
                Order,
                id=order_id
            )
            old_status = order.status
            # =========================
            # UPDATE STATUS
            # =========================
            if old_status != new_status:
                order.status = new_status
                # save -> trigger signal
                order.save()
                messages.success(
                    request,
                    f"Status pesanan "
                    f"#{order.id} "
                    f"berhasil diperbarui."
                )
            else:
                messages.info(
                    request,
                    f"Status pesanan "
                    f"#{order.id} "
                    f"tidak berubah."
                )
            return redirect(
                "shop:management_order_list"
            )
    # =========================
    # FILTER LIST
    # =========================
    status_filter = request.GET.get(
        "status"
    )
    orders = (
        Order.objects
        .select_related(
            "customer__user"
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )
    if status_filter:
        orders = orders.filter(
            status=status_filter
        )
    context = {
        "orders": orders,
        "order_status_choices":
            Order.SHIPPING_STATUS_CHOICES,
        "status_filter":
            status_filter,
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
# =========================
# API CHECK ONGKIR
# =========================
def api_check_ongkir(request):
    destination = request.GET.get("destination")
    courier = request.GET.get("courier")
    weight = request.GET.get("weight", 1000)
    # VALIDASI
    if not destination:
        return JsonResponse({
            "success": False,
            "message": "Destination wajib."
        }, status=400)
    if not courier:
        return JsonResponse({
            "success": False,
            "message": "Courier wajib."
        }, status=400)
    try:
        result = get_shipping_cost(
            destination=destination,
            weight=weight,
            courier=courier
        )
        # DEBUG TERMINAL
        print("========== ONGKIR RESULT ==========")
        print(result)
        print("===================================")
        return JsonResponse(result)
    except Exception as e:
        print("ONGKIR ERROR:", str(e))
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    
@require_POST
def check_shipping_cost(request):
    try:
        data = json.loads(request.body)
        destination = data.get("destination")
        weight = data.get("weight")
        courier = data.get("courier")
        result = get_shipping_cost(
            destination=destination,
            weight=weight,
            courier=courier
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=400)
# =========================
# PROVINCES API
# =========================
def province_api(request):
    try:
        response = get_provinces()
        return JsonResponse({
            "data": response.get("data", [])
        })
    except Exception as e:
        return JsonResponse({
            "data": [],
            "error": str(e)
        }, status=500)
# =========================
# CITIES API
# =========================
def city_api(request):
    province_id = request.GET.get("province_id")
    if not province_id:
        return JsonResponse({
            "data": [],
            "error": "province_id required"
        }, status=400)
    try:
        response = get_cities(province_id)
        return JsonResponse({
            "data": response.get("data", [])
        })
    except Exception as e:
        return JsonResponse({
            "data": [],
            "error": str(e)
        }, status=500)
# =========================
# SUBDISTRICTS API
# =========================
def subdistrict_api(request):
    city_id = request.GET.get("city_id")
    if not city_id:
        return JsonResponse({
            "data": [],
            "error": "city_id required"
        }, status=400)
    try:
        response = get_subdistricts(city_id)
        return JsonResponse({
            "data": response.get("data", [])
        })
    except Exception as e:
        return JsonResponse({
            "data": [],
            "error": str(e)
        }, status=500)