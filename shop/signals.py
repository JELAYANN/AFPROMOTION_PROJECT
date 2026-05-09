from django.db.models.signals import (post_save,pre_save)  # type: ignore
from django.dispatch import receiver  # type: ignore
from .models import Order
from .utils import (
    kirim_wa_otomatis,
    kirim_email_notifikasi
)
@receiver(pre_save, sender=Order)
def simpan_status_lama(
    sender,
    instance,
    **kwargs
):
    if instance.pk:
        try:
            old_instance = Order.objects.get(
                pk=instance.pk
            )
            instance._old_status = (
                old_instance.status
            )
        except Order.DoesNotExist:
            instance._old_status = None
# ==================================================
# NOTIFIKASI MULTI CHANNEL
# ==================================================
@receiver(post_save, sender=Order)
def notifikasi_order_multi_channel(
    sender,
    instance,
    created,
    **kwargs
):
    # =========================
    # SKIP ORDER BARU
    # =========================
    if created:
        return
    try:
        # =========================
        # CEGAH NOTIF GANDA
        # =========================
        old_status = getattr(
            instance,
            "_old_status",
            None
        )
        if old_status == instance.status:
            print(
                f"SKIP NOTIFICATION "
                f"(status tetap {instance.status})"
            )
            return
        # =========================
        # CUSTOMER DATA
        # =========================
        customer_user = instance.customer.user
        username = (
            customer_user.username
            if customer_user
            else "Customer"
        )
        email = (
            customer_user.email
            if customer_user
            else None
        )
        # =========================
        # PHONE
        # =========================
        phone = (
            instance.shipping_phone
            or getattr(
                instance.customer,
                "phone",
                None
            )
        )
        # =========================
        # BASIC DATA
        # =========================
        order_id = instance.id
        status = instance.status
        courier_code = (
            instance.courier_code or "-"
        )
        tracking_number = (
            instance.tracking_number or "-"
        )
        total_amount = (
            f"Rp {instance.total:,.0f}"
        )
        # =========================
        # EMAIL CONFIG
        # =========================
        email_info = {
            "PAID": {
                "subject":
                    f"Pembayaran Berhasil - AF Promotion #{order_id}",
                "template":
                    "emails/order_paid.html"
            },
            "PROCESSING": {
                "subject":
                    f"Pesanan Sedang Diproses - AF Promotion #{order_id}",
                "template":
                    "emails/order_processing.html"
            },
            "SHIPPED": {
                "subject":
                    f"Pesanan Dalam Pengiriman - AF Promotion #{order_id}",
                "template":
                    "emails/order_shipped.html"
            },
            "COMPLETED": {
                "subject":
                    f"Pesanan Selesai - AF Promotion #{order_id}",
                "template":
                    "emails/order_completed.html"
            },
            "CANCELLED": {
                "subject":
                    f"Pesanan Dibatalkan - AF Promotion #{order_id}",
                "template":
                    "emails/order_cancelled.html"
            }
        }
        # =========================
        # EMAIL
        # =========================
        if status in email_info and email:
            info = email_info[status]
            context = {
                "order": instance,
                "user": customer_user
            }
            kirim_email_notifikasi(
                subject=info["subject"],
                template=info["template"],
                context=context,
                recipient_email=email
            )
            print(
                f"✅ EMAIL {status} "
                f"terkirim ke {email}"
            )
        # =========================
        # WHATSAPP MESSAGE
        # =========================
        pesan_wa = ""
        # =========================
        # PAID
        # =========================
        if status == "PAID":
            pesan_wa = (
                f"Halo *{username}*,\n\n"
                f"Pembayaran untuk pesanan "
                f"*#{order_id}* sebesar "
                f"*{total_amount}* "
                f"telah kami terima. ✅\n\n"
                f"Pesanan Anda akan segera diproses.\n\n"
                f"Terima kasih telah berbelanja "
                f"di AF Promotion 🙏"
            )
        # =========================
        # PROCESSING
        # =========================
        elif status == "PROCESSING":
            pesan_wa = (
                f"Update Pesanan *#{order_id}* 🚀\n\n"
                f"Pesanan Anda sedang dalam tahap "
                f"*PROSES / PRODUKSI*.\n\n"
                f"Kami akan mengabari kembali "
                f"setelah pesanan dikirim."
            )
        # =========================
        # SHIPPED
        # =========================
        elif status == "SHIPPED":
            pesan_wa = (
                f"Pesanan *#{order_id}* "
                f"telah DIKIRIM 🚚\n\n"
                f"No. Resi: *{tracking_number}*\n"
                f"Kurir: {courier_code}\n\n"
                f"Silakan lakukan tracking "
                f"pengiriman 🙌"
            )
        # =========================
        # COMPLETED
        # =========================
        elif status == "COMPLETED":
            pesan_wa = (
                f"Pesanan *#{order_id}* "
                f"telah SELESAI ✅\n\n"
                f"Terima kasih *{username}* "
                f"telah mempercayai AF Promotion.\n"
                f"Sampai jumpa di order berikutnya 🙌"
            )
        # =========================
        # CANCELLED
        # =========================
        elif status == "CANCELLED":
            pesan_wa = (
                f"Pesanan *#{order_id}* "
                f"dibatalkan.\n\n"
                f"Jika ini terjadi karena "
                f"kendala pembayaran atau sistem,\n"
                f"silakan hubungi admin "
                f"AF Promotion."
            )
        # =========================
        # KIRIM WHATSAPP
        # =========================
        if pesan_wa and phone:
            try:
                kirim_wa_otomatis(
                    phone,
                    pesan_wa
                )
                print(
                    f"✅ WA {status} "
                    f"terkirim ke {phone}"
                )
            except Exception as e:
                print(
                    f"❌ Gagal kirim WA: {e}"
                )
    except Exception as e:
        print(
            f"❌ SIGNAL ERROR: {e}"
        )