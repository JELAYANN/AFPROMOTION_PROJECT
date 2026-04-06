# shop/signals.py
from django.db.models.signals import post_save # type: ignore
from django.dispatch import receiver # type: ignore
from django.template.loader import render_to_string # type: ignore
from django.core.mail import send_mail # type: ignore
from django.utils.html import strip_tags # type: ignore
from .models import Order
from .views import kirim_email_status_pesanan

@receiver(post_save, sender=Order)
def notifikasi_perubahan_status(sender, instance, created, **kwargs):
    if not created: # Hanya jika status diupdate
        email_info = {
            'PAID': {
                'subject': 'Pembayaran Diterima - AF Promotion',
                'template': 'emails/order_paid.html'
            },
            'PROCESSING': {
                'subject': 'Pesanan Sedang Diproses - AF Promotion',
                'template': 'emails/order_processing.html'
            },
            'SHIPPED': {
                'subject': 'Pesanan Dalam Pengiriman - AF Promotion',
                'template': 'emails/order_shipped.html'
            },
            'COMPLETED': {
                'subject': 'Pesanan Selesai - AF Promotion',
                'template': 'emails/order_completed.html'
            }
        }

        if instance.status in email_info:
            info = email_info[instance.status]
            context = {'order': instance, 'user': instance.customer.user}
            html_message = render_to_string(info['template'], context)
            
            send_mail(
                info['subject'],
                strip_tags(html_message),
                'AF Promotion <afpromotion9000@gmail.com>',
                [instance.customer.user.email],
                html_message=html_message
            )