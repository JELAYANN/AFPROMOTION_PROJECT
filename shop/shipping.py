import requests  # type: ignore
from django.conf import settings  # type: ignore

BASE_URL = "https://rajaongkir.komerce.id/api/v1"
# =========================
# DEFAULT HEADERS
# =========================
HEADERS = {
    "accept": "application/json",
    "key": settings.RAJAONGKIR_API_KEY,
}
# =========================================================
# 🟢 RAJAONGKIR - SHIPPING COST
# =========================================================
def get_shipping_cost(destination, weight, courier="jne"):
    url = f"{BASE_URL}/calculate/domestic-cost"
    payload = {
        "origin": int(settings.ORIGIN_SUBDISTRICT_ID),
        "destination": int(destination),
        "weight": int(weight),
        "courier": courier,
    }
    try:
        response = requests.post(
            url,
            headers=HEADERS,
            data=payload,
            timeout=30
        )
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json()
        }
    except requests.Timeout:
        return {
            "success": False,
            "message": "Request timeout"
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "message": str(e)
        }
# =========================================================
# 🔵 SHIPMENT LAYER (DUMMY - READY FOR KOMSHIP)
# =========================================================
class DummyShipmentProvider:
    def create_shipment(self, order):
        # simulasi AWB
        awb = f"DUMMY-AWB-{order.id}"
        return {
            "success": True,
            "awb": awb,
            "courier": order.courier_code,
            "message": "Dummy shipment created"
        }
    def track_waybill(self, courier, waybill):
        return {
            "success": True,
            "awb": waybill,
            "status": "IN_TRANSIT",
            "message": "Dummy tracking response"
        }
# =========================
# PROVIDER SELECTOR
# =========================
def get_shipment_provider():
    provider = getattr(settings, "SHIPMENT_PROVIDER", "dummy")
    if provider == "dummy":
        return DummyShipmentProvider()
    return DummyShipmentProvider()
# =========================
# CREATE SHIPMENT (MAIN)
# =========================
def create_shipment(order):
    provider = get_shipment_provider()
    result = provider.create_shipment(order)
    return normalize_shipment_result(result)
def normalize_shipment_result(result):
    return {
        "success": result.get("success", False),
        "awb":
            result.get("awb")
            or result.get("data", {}).get("awb")
            or result.get("data", {}).get("data", {}).get("awb"),
    }
# =========================
# TRACK WAYBILL (MAIN)
# =========================
def track_waybill(courier, waybill):
    provider = get_shipment_provider()
    return provider.track_waybill(courier, waybill)
# =========================================================
# 🟢 PROVINCE / CITY / SUBDISTRICT (JANGAN DIUBAH)
# =========================================================
def get_provinces():
    url = f"{BASE_URL}/destination/province"
    headers = {
        "accept": "application/json",
        "key": settings.RAJAONGKIR_API_KEY,
    }
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {
            "success": False,
            "message": "Request timeout",
            "data": []
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "message": str(e),
            "data": []
        }
def get_cities(province_id):
    url = f"{BASE_URL}/destination/city/{province_id}"
    headers = {
        "accept": "application/json",
        "key": settings.RAJAONGKIR_API_KEY,
    }
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {
            "success": False,
            "message": "Request timeout",
            "data": []
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "message": str(e),
            "data": []
        }
def get_subdistricts(city_id):
    url = f"{BASE_URL}/destination/district/{city_id}"
    headers = {
        "accept": "application/json",
        "key": settings.RAJAONGKIR_API_KEY,
    }
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {
            "success": False,
            "message": "Request timeout",
            "data": []
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "message": str(e),
            "data": []
        }