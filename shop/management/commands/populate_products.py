from django.core.management.base import BaseCommand     # type: ignore
from django.db import transaction                 # type: ignore
from shop.models import Color, Size, ProductCategory, Product, ProductVariant
# ── DATA KATEGORI ──────────────────────────────────────────────────────────────
CATEGORIES = [
    {
        "name": "KAOS POLOS",
        "description": "Kaos polos berbagai bahan premium tersedia dalam banyak pilihan warna dan ukuran.",
    },
    {
        "name": "KAOS POLO",
        "description": "Kaos polo berkerah dengan bahan premium, cocok untuk casual maupun seragam.",
    },
]
# ── DATA PRODUK ────────────────────────────────────────────────────────────────
PRODUCTS = [
    {
        "category": "KAOS POLOS",
        "name": "Kaos Polos Cotton Combed 20s",
        "description": (
            "Kaos polos bahan 100% Cotton Combed 20s premium, gramasi 190-200 gsm. "
            "Tebal, lembut, adem, dan tidak mudah melar. "
            "Cocok untuk sablon maupun pemakaian harian. "
            "Tersedia dalam berbagai pilihan warna."
        ),
        "base_price": 55000,
        "sizes": ["L", "XXL", "XXXL"],
    },
    {
        "category": "KAOS POLOS",
        "name": "Kaos Polos Cotton Combed 24s",
        "description": (
            "Kaos polos bahan 100% Cotton Combed 24s premium, gramasi 170-210 gsm. "
            "Lebih ringan dari 20s namun tetap nyaman dan adem. "
            "Cocok untuk aktivitas sehari-hari maupun dijadikan seragam."
        ),
        "base_price": 52000,
        "sizes": ["S", "M", "L", "XL", "XXL", "XXXL"],
    },
    {
        "category": "KAOS POLOS",
        "name": "Kaos Polos Cotton Combed 30s",
        "description": (
            "Kaos polos bahan 100% Cotton Combed 30s premium, gramasi 140-155 gsm. "
            "Ringan, tipis, dan sangat adem. "
            "Pilihan terbaik untuk iklim tropis dan aktivitas outdoor. "
            "Tersedia ukuran hingga 5XL."
        ),
        "base_price": 42000,
        "sizes": ["S", "M", "L", "XL", "XXL", "XXXL", "XXXXL", "XXXXXL"],
    },
    {
        "category": "KAOS POLOS",
        "name": "Kaos Polos Polyester 24s",
        "description": (
            "Kaos polos bahan Polyester 24s premium. "
            "Ringan, cepat kering, dan sangat adem. "
            "Sangat cocok untuk olahraga, aktivitas luar ruangan, "
            "maupun kebutuhan seragam tim."
        ),
        "base_price": 35000,
        "sizes": ["S", "M", "L", "XL", "XXL"],
    },
    {
        "category": "KAOS POLO",
        "name": "Polo Polos Bahan Lakos PE",
        "description": (
            "Kaos polo polos bahan Lakos PE premium. "
            "Berkerah rapi, ringan, dan adem. "
            "Cocok untuk casual, seragam kantor, "
            "maupun kegiatan formal semi-resmi. "
            "Tersedia berbagai pilihan warna."
        ),
        "base_price": 52000,
        "sizes": ["S", "M", "L", "XL", "XXL"],
    },
]
class Command(BaseCommand):
    help = "Populate Produk Polos beserta semua Variant (warna x ukuran) untuk AF PROMOTION"
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== AF PROMOTION — Populate Produk Polos & Variants ===\n"
        ))
        # ── Cek warna & ukuran tersedia ─────────────────────────────────────
        all_colors = list(Color.objects.all())
        if not all_colors:
            self.stdout.write(self.style.ERROR(
                "✗ Tidak ada data warna! Jalankan dulu: python manage.py populate_master_data"
            ))
            return
        self.stdout.write(f"  Warna tersedia : {len(all_colors)} warna")
        with transaction.atomic():
            # ── 1. AMBIL KATEGORI (case-insensitive) ────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n» Memastikan Kategori..."))
            category_map = {}
            for cat_data in CATEGORIES:
                cat = ProductCategory.objects.filter(name__iexact=cat_data["name"]).first()
                if cat:
                    category_map[cat_data["name"]] = cat
                    self.stdout.write(f"  {self.style.WARNING('– Ada')}     {cat.name}")
                else:
                    cat = ProductCategory.objects.create(
                        name=cat_data["name"],
                        description=cat_data["description"],
                    )
                    category_map[cat_data["name"]] = cat
                    self.stdout.write(f"  {self.style.SUCCESS('✓ Dibuat')}  {cat.name}")
            # ── 2. INSERT PRODUK & VARIANTS ─────────────────────────────────
            self.stdout.write(self.style.MIGRATE_LABEL("\n» Memasukkan Produk & Variants..."))
            total_products_created = 0
            total_variants_created = 0
            total_variants_skipped = 0
            for prod_data in PRODUCTS:
                category_obj = category_map[prod_data["category"]]
                product, prod_created = Product.objects.get_or_create(
                    name=prod_data["name"],
                    defaults={
                        "category":    category_obj,
                        "description": prod_data["description"],
                        "price":       prod_data["base_price"],
                        "is_active":   True,
                    },
                )
                if prod_created:
                    total_products_created += 1
                    self.stdout.write(
                        f"\n  {self.style.SUCCESS('✓ PRODUK BARU')}  {product.name}"
                        f"  (harga dasar: Rp {prod_data['base_price']:,})"
                    )
                else:
                    self.stdout.write(
                        f"\n  {self.style.WARNING('– ADA')}        {product.name}"
                        f"  (cek & tambah variants yang belum ada)"
                    )
                sizes_in_order = prod_data["sizes"]
                v_created = 0
                v_skipped = 0
                for color_obj in all_colors:
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
                        price_override = prod_data["base_price"] + (idx * 5000)
                        _, var_created = ProductVariant.objects.get_or_create(
                            product=product,
                            color=color_obj,
                            size=size_obj,
                            defaults={
                                "stock":          10,
                                "price_override": price_override,
                            },
                        )
                        if var_created:
                            v_created += 1
                        else:
                            v_skipped += 1
                total_variants_created += v_created
                total_variants_skipped += v_skipped
                self.stdout.write(
                    f"    Variants: {self.style.SUCCESS(str(v_created))} dibuat"
                    f", {self.style.WARNING(str(v_skipped))} sudah ada"
                    f"  [{len(all_colors)} warna × {len(sizes_in_order)} ukuran]"
                )
        # ── SUMMARY ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n─────────────────────────────────────"))
        self.stdout.write(f"  Produk dibuat   : {self.style.SUCCESS(str(total_products_created))}")
        self.stdout.write(f"  Variants dibuat : {self.style.SUCCESS(str(total_variants_created))}")
        self.stdout.write(f"  Variants ada    : {self.style.WARNING(str(total_variants_skipped))}")
        self.stdout.write(self.style.SUCCESS(
            "\n=== Selesai! Semua produk & variants berhasil dimasukkan. ===\n"
        ))