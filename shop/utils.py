import requests # type: ignore

def kirim_wa_otomatis(phone, message):

    api_token = 'Mff1Ames1N97h1vkoYXD' 
    phone = str(phone).replace(" ", "").replace("-", "").replace("+", "")
    
    if phone.startswith('0'):
        phone = '62' + phone[1:]
    elif phone.startswith('8'):
        phone = '62' + phone
    elif not phone.startswith('62'):
        phone = '62' + phone

    url = "https://api.fonnte.com/send"
    
    payload = {
        'target': phone,
        'message': message,
        'countryCode': '62', 
    }
    
    headers = {
        'Authorization': api_token 
    }
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        result = response.json()
        if result.get('status'):
            print(f"✅ WA TERKIRIM ke {phone}: {message[:30]}...")
        else:
            print(f"❌ WA GAGAL ke {phone}. Pesan: {result.get('reason')}")
            
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"⚠️ ERROR KONEKSI API WA: {e}")
        return None