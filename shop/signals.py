from django.db.models.signals import post_save # type: ignore
from django.dispatch import receiver # type: ignore
from django.template.loader import render_to_string, TemplateDoesNotExist    # type: ignore
from django.core.mail import send_mail # type: ignore
from django.utils.html import strip_tags # type: ignore

from .models import Order
from .utils import kirim_wa_otomatis


@receiver(post_save, sender=Order)
def notifikasi_order_multi_channel(sender, instance, created, **kwargs):
    """
    Kirim Email + WhatsApp otomatis
    ketika status order berubah.
    """

    # Jangan kirim notif saat order baru dibuat
    if created:
        return

    try:
        customer_user = instance.customer.user

        username = customer_user.username
        email = customer_user.email

        # fallback aman
        phone = getattr(instance.customer, 'phone', None)

        order_id = instance.id
        status = instance.status

        # =========================
        # EMAIL CONFIG
        # =========================
        email_info = {
            'PAID': {
                'subject': f'Pembayaran Diterima - AF Promotion #{order_id}',
                'template': 'emails/order_paid.html'
            },

            'PROCESSING': {
                'subject': f'Pesanan Sedang Diproses - AF Promotion #{order_id}',
                'template': 'emails/order_processing.html'
            },

            'SHIPPED': {
                'subject': f'Pesanan Dalam Pengiriman - AF Promotion #{order_id}',
                'template': 'emails/order_shipped.html'
            },

            'COMPLETED': {
                'subject': f'Pesanan Selesai - AF Promotion #{order_id}',
                'template': 'emails/order_completed.html'
            },

            'CANCELLED': {
                'subject': f'Pesanan Dibatalkan - AF Promotion #{order_id}',
                'template': 'emails/order_cancelled.html'
            }
        }

        # =========================
        # KIRIM EMAIL
        # =========================
        if status in email_info:

            info = email_info[status]

            context = {
                'order': instance,
                'user': customer_user
            }

            try:
                html_message = render_to_string(
                    info['template'],
                    context
                )

                send_mail(
                    info['subject'],
                    strip_tags(html_message),
                    'AF Promotion <afpromotion9000@gmail.com>',
                    [email],
                    html_message=html_message,
                    fail_silently=True
                )

                print(f"✅ EMAIL {status} terkirim ke {email}")

            except TemplateDoesNotExist:
                print(f"⚠️ Template {info['template']} tidak ditemukan")

            except Exception as e:
                print(f"❌ Gagal kirim email: {e}")

        # =========================
        # WHATSAPP MESSAGE
        # =========================
        pesan_wa = ""

        if status == 'PAID':

            pesan_wa = (
                f"Halo *{username}*,\n\n"
                f"Pembayaran untuk pesanan *#{order_id}* "
                f"telah kami terima. ✅\n\n"
                f"Pesanan Anda akan segera diproses.\n"
                f"Terima kasih telah berbelanja di AF Promotion 🙏"
            )

        elif status == 'PROCESSING':

            pesan_wa = (
                f"Update Pesanan *#{order_id}* 🚀\n\n"
                f"Pesanan Anda sedang dalam tahap "
                f"*PROSES / PRODUKSI*.\n\n"
                f"Kami akan mengabari kembali "
                f"setelah pesanan dikirim."
            )

        elif status == 'SHIPPED':

            # fallback aman jika field belum ada
            resi = getattr(instance, 'tracking_number', '-')

            pesan_wa = (
                f"Pesanan *#{order_id}* telah DIKIRIM 🚚\n\n"
                f"No. Resi: *{resi}*\n"
                f"Kurir: {instance.courier_code}\n\n"
                f"Terima kasih telah berbelanja di AF Promotion ❤️"
            )

        elif status == 'COMPLETED':

            pesan_wa = (
                f"Pesanan *#{order_id}* telah SELESAI ✅\n\n"
                f"Terima kasih *{username}* "
                f"telah mempercayai AF Promotion.\n"
                f"Sampai jumpa di order berikutnya 🙌"
            )

        elif status == 'CANCELLED':

            pesan_wa = (
                f"Pesanan *#{order_id}* dibatalkan.\n\n"
                f"Jika ini terjadi karena kendala pembayaran "
                f"atau sistem, silakan hubungi admin AF Promotion."
            )

        # =========================
        # KIRIM WHATSAPP
        # =========================
        if pesan_wa and phone:

            try:
                kirim_wa_otomatis(phone, pesan_wa)
                print(f"✅ WA {status} terkirim ke {phone}")

            except Exception as e:
                print(f"❌ Gagal kirim WA: {e}")

    except Exception as e:
        print(f"❌ SIGNAL ERROR: {e}")