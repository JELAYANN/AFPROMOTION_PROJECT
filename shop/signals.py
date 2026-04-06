from django.db.models.signals import post_save # type: ignore
from django.dispatch import receiver # type: ignore
from django.template.loader import render_to_string, TemplateDoesNotExist # type: ignore
from django.core.mail import send_mail # type: ignore
from django.utils.html import strip_tags # type: ignore
from .models import Order
from .utils import kirim_wa_otomatis

@receiver(post_save, sender=Order)
def notifikasi_order_multi_channel(sender, instance, created, **kwargs):
    """
    Signal untuk mengirim notifikasi Email dan WhatsApp secara otomatis 
    setiap kali ada perubahan status pada Order.
    """
    if not created:  # Hanya dijalankan jika status di-update (bukan saat baru dibuat)
        
        customer_user = instance.customer.user
        phone = instance.customer.phone
        username = customer_user.username
        order_id = instance.id
        status = instance.status

        # --- 1. KONFIGURASI EMAIL ---
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
            }
        }

        # --- 2. LOGIKA PENGIRIMAN EMAIL ---
        if status in email_info:
            info = email_info[status]
            context = {'order': instance, 'user': customer_user}
            
            try:
                html_message = render_to_string(info['template'], context)
                send_mail(
                    info['subject'],
                    strip_tags(html_message),
                    'AF Promotion <afpromotion9000@gmail.com>',
                    [customer_user.email],
                    html_message=html_message,
                    fail_silently=True # Agar tidak crash jika SMTP bermasalah
                )
                print(f"✅ Email Status {status} terkirim ke {customer_user.email}")
            except TemplateDoesNotExist:
                print(f"⚠️ Template {info['template']} tidak ditemukan, email gagal dikirim.")
            except Exception as e:
                print(f"❌ Gagal kirim email: {e}")

        # --- 3. LOGIKA PENGIRIMAN WHATSAPP ---
        pesan_wa = ""
        
        if status == 'PAID':
            pesan_wa = (
                f"Halo *{username}*,\n\n"
                f"Pembayaran untuk pesanan *#{order_id}* telah kami terima. "
                f"Pesanan Anda masuk antrean produksi. Terimakasih! 🙏"
            )
        
        elif status == 'PROCESSING':
            pesan_wa = (
                f"Update Pesanan *#{order_id}*:\n\n"
                f"Pesanan Anda atas nama *{username}* sedang dalam tahap *PENGERJAAN*. 🛠️\n"
                f"Kami akan infokan kembali jika sudah siap kirim."
            )
        
        elif status == 'SHIPPED':
            resi = instance.tracking_number if instance.tracking_number else "-"
            pesan_wa = (
                f"Kabar gembira! Pesanan *#{order_id}* sudah *DIKIRIM*. 🚚\n\n"
                f"No. Resi: *{resi}*\n"
                f"Kurir: {instance.courier_code}\n\n"
                f"Terima kasih telah belanja di AF Promotion!"
            )
            
        elif status == 'COMPLETED':
            pesan_wa = (
                f"Pesanan *#{order_id}* telah *SELESAI*. ✅\n\n"
                f"Terima kasih *{username}* telah mempercayai AF Promotion. "
                f"Sampai jumpa di order berikutnya!"
            )

        # Kirim WA jika pesan sudah disiapkan dan nomor HP tersedia
        if pesan_wa and phone:
            kirim_wa_otomatis(phone, pesan_wa)