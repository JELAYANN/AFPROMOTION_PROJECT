from django.core.management.base import BaseCommand     # type: ignore
from django.db import transaction  # type: ignore
from shop.models import (
    Size, Product, CustomService, CustomProduct, CustomProductVariant
)
# ── DATA CUSTOM SERVICES ───────────────────────────────────────────────────────
SERVICES = [
    {"name": "Sablon DTF A4",       "service_type": "SABLON", "additional_price": 15000},
    {"name": "Sablon DTF A3",       "service_type": "SABLON", "additional_price": 25000},
    {"name": "Sablon DTF A2",       "service_type": "SABLON", "additional_price": 35000},
    {"name": "Sablon Manual",       "service_type": "SABLON", "additional_price": 10000},
    {"name": "Bordir Logo Kecil",   "service_type": "BORDIR", "additional_price": 20000},
    {"name": "Bordir Logo Sedang",  "service_type": "BORDIR", "additional_price": 30000},
    {"name": "Bordir Logo Besar",   "service_type": "BORDIR", "additional_price": 45000},
]
# ── DATA CUSTOM PRODUCTS ───────────────────────────────────────────────────────
CUSTOM_PRODUCTS = [
    {
        "name":         "Kaos DTF Custom Printing",
        "base_product": "Kaos Polos Cotton Combed 24s",
        "description":  (
            "Kaos custom dengan teknik cetak DTF (Direct to Film) berkualitas tinggi. "
            "Warna tajam, detail halus, dan tahan lama. "
            "Cocok untuk merchandise, komunitas, atau kebutuhan personal. "
            "Desain bebas sesuai keinginan."
        ),
        "services":     ["Sablon DTF A4", "Sablon DTF A3", "Sablon DTF A2"],
        "sizes":        ["S", "M", "L", "XL", "XXL", "XXXL"],
        "base_price":   58000,
        "is_active":    True,
    },
    {
        "name":         "Kaos Bordir Custom Desain Eksklusif",
        "base_product": "Kaos Polos Cotton Combed 24s",
        "description":  (
            "Kaos custom dengan teknik bordir eksklusif. "
            "Tampilan elegan dan premium, cocok untuk seragam kantor, "
            "komunitas, maupun hadiah eksklusif. "
            "Tersedia desain bordir logo, tulisan, maupun motif bebas."
        ),
        "services":     ["Bordir Logo Kecil", "Bordir Logo Sedang", "Bordir Logo Besar"],
        "sizes":        ["S", "M", "L", "XL", "XXL", "XXXL"],
        "base_price":   63000,
        "is_active":    True,
    },
    {
        "name":         "Kaos Polo Custom Sablon DTF",
        "base_product": "Polo Polos Bahan Lakos PE",
        "description":  (
            "Kaos polo custom dengan sablon DTF (Direct to Film). "
            "Cetak penuh warna dengan detail tajam langsung di atas polo berkerah. "
            "Ideal untuk seragam tim, event, atau branding perusahaan."
        ),
        "services":     ["Sablon DTF A4", "Sablon DTF A3"],
        "sizes":        ["S", "M", "L", "XL", "XXL"],
        "base_price":   59000,
        "is_active":    True,
    },
    {
        "name":         "Kaos Polo Bordir Custom Elegan",
        "base_product": "Polo Polos Bahan Lakos PE",
        "description":  (
            "Kaos polo custom dengan bordir elegan. "
            "Kesan profesional dan premium, cocok untuk seragam kantor "
            "atau acara formal semi-resmi. "
            "Tersedia bordir logo, nama, maupun inisial."
        ),
        "services":     ["Bordir Logo Kecil", "Bordir Logo Sedang", "Bordir Logo Besar"],
        "sizes":        ["S", "M", "L", "XL", "XXL"],
        "base_price":   67000,
        "is_active":    True,
    },
    {
        "name":         "Kaos Polo Custom Bentuk Stylish",
        "base_product": "Polo Polos Bahan Lakos PE",
        "description":  (
            "Kaos polo custom dengan desain potongan stylish dan modern. "
            "Bisa dikombinasikan dengan sablon maupun bordir sesuai kebutuhan. "
            "Tampil beda dan percaya diri dengan desain eksklusif milikmu."
        ),
        "services":     ["Sablon DTF A4", "Sablon DTF A3", "Bordir Logo Kecil", "Bordir Logo Sedang"],
        "sizes":        ["S", "M", "L", "XL", "XXL"],
        "base_price":   75000,
        "is_active":    True,
    },
    {
        "name":         "Kaos Jersey Custom Komunitas & Tim",
        "base_product": "Kaos Polos Polyester 24s",
        "description":  (
            "Jersey custom full printing untuk komunitas, tim olahraga, maupun event. "
            "Bahan polyester adem dan cepat kering. "
            "Desain bebas dengan nama dan nomor punggung sesuai permintaan."
        ),
        "services":     ["Sablon DTF A4", "Sablon DTF A3", "Sablon DTF A2"],
        "sizes":        ["S", "M", "L", "XL", "XXL", "XXXL"],
        "base_price":   120000,
        "is_active":    True,
    },
    {
        "name":         "Seragam Olahraga Custom Desain Bebas",
        "base_product": "Kaos Polos Polyester 24s",
        "description":  (
            "Seragam olahraga custom dengan desain bebas sesuai keinginan. "
            "Bahan polyester ringan dan adem, cocok untuk aktivitas fisik. "
            "Bisa untuk sekolah, instansi, komunitas, atau tim olahraga."
        ),
        "services":     ["Sablon DTF A4", "Sablon DTF A3", "Sablon DTF A2", "Sablon Manual"],
        "sizes":        ["S", "M", "L", "XL", "XXL", "XXXL"],
        "base_price":   100000,
        "is_active":    True,
    },
    {
        "name":         "Seragam Kerja Custom Berbahan Drill",
        "base_product": "Kaos Polos Cotton Combed 24s",
        "description":  (
            "Seragam kerja custom berbahan drill premium. "
            "Kain tebal, rapi, dan tahan lama, cocok untuk seragam instansi, "
            "perusahaan, maupun organisasi. "
            "Tersedia bordir logo dan nama sesuai kebutuhan."
        ),
        "services":     ["Bordir Logo Kecil", "Bordir Logo Sedang", "Bordir Logo Besar"],
        "sizes":        ["S", "M", "L", "XL", "XXL", "XXXL"],
        "base_price":   195000,
        "is_active":    True,
    },
    {
        "name":         "Bordir Logo Custom Kebutuhan Branding",
        "base_product": "Kaos Polos Cotton Combed 24s",
        "description":  (
            "Layanan bordir logo custom untuk berbagai kebutuhan branding. "
            "Cocok untuk kaos, polo, jaket, topi, dan pakaian lainnya. "
            "Kualitas bordir rapi dan detail, dengan benang premium tahan lama. "
            "Harga per logo, minimum order dapat dikonfirmasi via chat."
        ),
        "services":     ["Bordir Logo Kecil", "Bordir Logo Sedang", "Bordir Logo Besar"],
        "sizes":        ["S", "M", "L", "XL", "XXL", "XXXL"],
        "base_price":   63000,
        "is_active":    True,
    },
]
class Command(BaseCommand):
    help = "Populate Custom Services, Custom Products, dan Variants untuk AF PROMOTION"
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== AF PROMOTION — Populate Custom Products ===\n"
        ))
        with transaction.atomic():
            # ── 1. INSERT CUSTOM SERVICES ────────────────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("» Memasukkan Custom Services..."))
            service_map = {}
            svc_created = 0
            svc_skipped = 0
            for svc_data in SERVICES:
                svc, created = CustomService.objects.get_or_create(
                    name=svc_data["name"],
                    defaults={
                        "service_type":     svc_data["service_type"],
                        "additional_price": svc_data["additional_price"],
                    },
                )
                service_map[svc.name] = svc
                if created:
                    svc_created += 1
                    label = f"[{svc.service_type}]"
                    self.stdout.write(
                        f"  {self.style.SUCCESS('✓')} {svc.name:<25} {label:<10}"
                        f"  +Rp {svc.additional_price:,}"
                    )
                else:
                    svc_skipped += 1
                    self.stdout.write(
                        f"  {self.style.WARNING('–')} {svc.name:<25} sudah ada, dilewati"
                    )
            self.stdout.write(
                f"\n  Services: {self.style.SUCCESS(str(svc_created))} dibuat, "
                f"{self.style.WARNING(str(svc_skipped))} dilewati\n"
            )
            # ── 2. INSERT CUSTOM PRODUCTS & VARIANTS ────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("» Memasukkan Custom Products & Variants..."))
            total_cp_created  = 0
            total_cpv_created = 0
            total_cpv_skipped = 0
            for cp_data in CUSTOM_PRODUCTS:
                # -- Cari base product --
                base_product = Product.objects.filter(
                    name__iexact=cp_data["base_product"]
                ).first()
                if not base_product:
                    self.stdout.write(
                        self.style.ERROR(
                            f"\n  ✗ Base product '{cp_data['base_product']}' tidak ditemukan! "
                            f"Jalankan populate_products terlebih dahulu."
                        )
                    )
                    continue
                # -- Buat / ambil CustomProduct --
                cp, cp_created = CustomProduct.objects.get_or_create(
                    name=cp_data["name"],
                    defaults={
                        "base_product": base_product,
                        "description":  cp_data["description"],
                        "is_active":    cp_data["is_active"],
                        "image":        "",
                    },
                )
                if cp_created:
                    total_cp_created += 1
                    self.stdout.write(
                        f"\n  {self.style.SUCCESS('✓ BARU')}  {cp.name}"
                        f"\n           Base: {base_product.name}"
                    )
                else:
                    self.stdout.write(
                        f"\n  {self.style.WARNING('– ADA')}   {cp.name}"
                        f"  (update services & cek variants)"
                    )
                # -- Pasang available_services (M2M) --
                for svc_name in cp_data["services"]:
                    svc_obj = service_map.get(svc_name)
                    if svc_obj:
                        cp.available_services.add(svc_obj)
                svc_names = ", ".join(cp_data["services"])
                self.stdout.write(f"           Services: {svc_names}")
                # -- Buat CustomProductVariants per ukuran --
                sizes_in_order = cp_data["sizes"]
                cpv_created = 0
                cpv_skipped = 0
                for idx, size_name in enumerate(sizes_in_order):
                    try:
                        size_obj = Size.objects.get(name=size_name)
                    except Size.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"    ⚠ Ukuran '{size_name}' tidak ada di DB, dilewati"
                            )
                        )
                        continue
                    price = cp_data["base_price"] + (idx * 5000)
                    _, var_created = CustomProductVariant.objects.get_or_create(
                        custom_product=cp,
                        size=size_obj,
                        defaults={
                            "price": price,
                            "stock": 0,
                        },
                    )
                    if var_created:
                        cpv_created += 1
                    else:
                        cpv_skipped += 1
                total_cpv_created += cpv_created
                total_cpv_skipped += cpv_skipped
                self.stdout.write(
                    f"           Variants: {self.style.SUCCESS(str(cpv_created))} dibuat"
                    f", {self.style.WARNING(str(cpv_skipped))} sudah ada"
                    f"  [{len(sizes_in_order)} ukuran]"
                )
        # ── SUMMARY ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n─────────────────────────────────────"))
        self.stdout.write(f"  Services dibuat         : {self.style.SUCCESS(str(svc_created))}")
        self.stdout.write(f"  Custom products dibuat  : {self.style.SUCCESS(str(total_cp_created))}")
        self.stdout.write(f"  Variants dibuat         : {self.style.SUCCESS(str(total_cpv_created))}")
        self.stdout.write(f"  Variants sudah ada      : {self.style.WARNING(str(total_cpv_skipped))}")
        self.stdout.write(self.style.SUCCESS(
            "\n=== Selesai! Semua custom products & variants berhasil dimasukkan. ===\n"
        ))
