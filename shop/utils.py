import requests # type: ignore

def kirim_wa_otomatis(phone, message):

    api_token = 'Mff1Ames1N97h1vkoYXD' 
    
    # --- LOGIKA MEMBERSIHKAN NOMOR HP ---
    # Hilangkan spasi atau karakter aneh jika ada
    phone = str(phone).replace(" ", "").replace("-", "").replace("+", "")
    
    if phone.startswith('0'):
        # Ubah 0812... menjadi 62812...
        phone = '62' + phone[1:]
    elif phone.startswith('8'):
        # Ubah 812... menjadi 62812...
        phone = '62' + phone
    elif not phone.startswith('62'):
        # Jika tidak diawali 62, asumsikan itu format lokal dan tambahkan 62
        phone = '62' + phone

    # --- KONFIGURASI API ---
    url = "https://api.fonnte.com/send"
    
    payload = {
        'target': phone,
        'message': message,
        'countryCode': '62', # Default kode negara Indonesia
    }
    
    headers = {
        'Authorization': api_token # Fonnte menggunakan token langsung
    }

    # --- PROSES PENGIRIMAN ---
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        result = response.json()
        
        # Cetak hasil ke terminal Django untuk monitoring
        if result.get('status'):
            print(f"✅ WA TERKIRIM ke {phone}: {message[:30]}...")
        else:
            print(f"❌ WA GAGAL ke {phone}. Pesan: {result.get('reason')}")
            
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"⚠️ ERROR KONEKSI API WA: {e}")
        return None