import requests  # type: ignore
from django.conf import settings  # type: ignore
from django.core.mail import send_mail  # type: ignore
from django.template.loader import render_to_string, TemplateDoesNotExist  # type: ignore
from django.utils.html import strip_tags  # type: ignore

# =========================
# WHATSAPP SENDER
# =========================
def kirim_wa_otomatis(phone, message):
    phone = str(phone).replace(" ", "").replace("-", "").replace("+", "")
    # =========================
    # FORMAT NOMOR
    # =========================
    if phone.startswith('0'):
        phone = '62' + phone[1:]
    elif phone.startswith('8'):
        phone = '62' + phone
    elif not phone.startswith('62'):
        phone = '62' + phone
    url     = "https://api.fonnte.com/send"
    payload = {'target': phone, 'message': message, 'countryCode': '62'}
    headers = {'Authorization': settings.FONNTE_TOKEN}
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        result   = response.json()
        if result.get('status'):
            print(f"✅ WA TERKIRIM ke {phone}: {message[:30]}...")
        else:
            print(f"❌ WA GAGAL ke {phone}. Pesan: {result.get('reason')}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"⚠️ ERROR KONEKSI API WA: {e}")
        return None
# =========================
# EMAIL SENDER
# =========================
def kirim_email_notifikasi(subject, template, context, recipient_email):
    try:
        html_message  = render_to_string(template, context)
        plain_message = strip_tags(html_message)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        print(f"✅ EMAIL terkirim ke {recipient_email}")
        return True
    except TemplateDoesNotExist:
        print(f"❌ TEMPLATE EMAIL {template} TIDAK DITEMUKAN")
        return False
    except Exception as e:
        print(f"❌ GAGAL KIRIM EMAIL: {e}")
        return False