from django.core.management.base import BaseCommand      # type: ignore
from shop.models import Color, Size
COLORS = [
    {"name": "Putih",        "hex_code": "#FFFFFF"},
    {"name": "Hitam",        "hex_code": "#1A1A1A"},
    {"name": "Abu-abu Tua",  "hex_code": "#555555"},
    {"name": "Abu-abu Muda", "hex_code": "#AAAAAA"},
    {"name": "Cream",        "hex_code": "#F5F5DC"},
    {"name": "Navy",         "hex_code": "#001F5B"},
    {"name": "Biru Langit",  "hex_code": "#5BA4D4"},
    {"name": "Biru Turkis",  "hex_code": "#00ADB5"},
    {"name": "Tosca",        "hex_code": "#007B72"},
    {"name": "Merah",        "hex_code": "#CC2200"},
    {"name": "Maroon",       "hex_code": "#7A1010"},
    {"name": "Kuning",       "hex_code": "#FFD700"},
    {"name": "Kuning Mustard","hex_code": "#C8900A"},
    {"name": "Hijau Army",   "hex_code": "#4B5320"},
    {"name": "Hijau Botol",  "hex_code": "#1B5E20"},
    {"name": "Ungu",         "hex_code": "#6A0DAD"},
    {"name": "Lilac",        "hex_code": "#B39DDB"},
    {"name": "Pink",         "hex_code": "#F06292"},
    {"name": "Orange",       "hex_code": "#E65100"},
    {"name": "Salem",        "hex_code": "#E07B6A"},
]
SIZES = ["S", "M", "L", "XL", "XXL", "XXXL", "XXXXL", "XXXXXL"]
class Command(BaseCommand):
    help = "Populate master data: Colors dan Sizes untuk produk AF PROMOTION"
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== AF PROMOTION — Populate Master Data ===\n"))
        # ── INSERT COLORS ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_LABEL("» Memasukkan data Warna..."))
        color_created = 0
        color_skipped = 0
        for data in COLORS:
            obj, created = Color.objects.get_or_create(
                name=data["name"],
                defaults={"hex_code": data["hex_code"]}
            )
            if created:
                color_created += 1
                self.stdout.write(
                    f"  {self.style.SUCCESS('✓')} {obj.name:<20} {obj.hex_code}"
                )
            else:
                color_skipped += 1
                self.stdout.write(
                    f"  {self.style.WARNING('–')} {obj.name:<20} sudah ada, dilewati"
                )
        self.stdout.write(
            f"\n  Total warna: {self.style.SUCCESS(str(color_created))} ditambahkan, "
            f"{self.style.WARNING(str(color_skipped))} dilewati\n"
        )
        # ── INSERT SIZES ───────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_LABEL("» Memasukkan data Ukuran..."))
        size_created = 0
        size_skipped = 0
        for size_name in SIZES:
            obj, created = Size.objects.get_or_create(name=size_name)
            if created:
                size_created += 1
                self.stdout.write(f"  {self.style.SUCCESS('✓')} {obj.name}")
            else:
                size_skipped += 1
                self.stdout.write(f"  {self.style.WARNING('–')} {obj.name} sudah ada, dilewati")
        self.stdout.write(
            f"\n  Total ukuran: {self.style.SUCCESS(str(size_created))} ditambahkan, "
            f"{self.style.WARNING(str(size_skipped))} dilewati\n"
        )
        # ── SUMMARY ───────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("=== Selesai! Master data berhasil dimasukkan. ===\n"))
