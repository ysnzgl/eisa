"""python manage.py seed_dev — Dev ortami icin dummy veri tohumla (eczane, kiosk, admin/eczaci kullanici)."""
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from apps.lookups.seed import seed_lookups
from apps.lookups.models import Il
from apps.pharmacies.models import Eczane, Kiosk
from apps.users.models import Kullanici


class Command(BaseCommand):
    help = "Dev ortami icin dummy veri tohumlar: lookups, eczane, kiosk, admin ve eczaci kullanicilar."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=== DEV SEED STARTED ==="))

        # 1. Lookups tohumla (Il, Ilce, Cinsiyet, YasAraligi)
        self.stdout.write("Step 1: Lookup tablolarini tohumluyorum...")
        counts = seed_lookups()
        self.stdout.write(self.style.SUCCESS(
            f"✓ Lookup tohumlama tamamlandi: "
            f"il+{counts['il']}, ilce+{counts['ilce']}, "
            f"cinsiyet+{counts['cinsiyet']}, yas_araligi+{counts['yas_araligi']}"
        ))

        # 2. Eczane olustur (Istanbul)
        self.stdout.write("Step 2: Dummy eczane olusturuyorum...")
        il = Il.objects.get(ad="Istanbul")
        ilce = il.ilceler.first()
        
        eczane, created = Eczane.objects.get_or_create(
            ad="Demo Eczanesi",
            defaults={
                "il": il,
                "ilce": ilce,
                "adres": "Demo Caddesi No. 1, Kadikoy, Istanbul",
                "sahip_adi": "Demo Eczacı",
                "telefon": "0212 1234567",
                "eczane_kodu": "DEMO001",
                "aktif": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Eczane olusturuldu: {eczane.ad} (ID: {eczane.id})"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Eczane zaten var: {eczane.ad}"))

        # 3. Kiosk olustur
        self.stdout.write("Step 3: Dummy kiosk olusturuyorum...")
        mac_address = "00:11:22:33:44:55"
        app_key = "demo_kiosk_key_12345"
        
        kiosk, created = Kiosk.objects.get_or_create(
            mac_adresi=mac_address,
            defaults={
                "eczane": eczane,
                "uygulama_anahtari": app_key,
                "aktif": True,
                "son_goruldu": now(),
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Kiosk olusturuldu (MAC: {kiosk.mac_adresi})"))
            self.stdout.write(f"  App Key: {kiosk.uygulama_anahtari}")
            self.stdout.write(f"  Eczane: {eczane.ad}")
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Kiosk zaten var (MAC: {kiosk.mac_adresi})"))

        # 4. Admin user olustur
        self.stdout.write("Step 4: Admin kullanicisi olusturuyorum...")
        admin_user, created = Kullanici.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@eisa.local",
                "first_name": "Admin",
                "last_name": "User",
                "rol": Kullanici.Rol.SUPERADMIN,
                "eczane": None,  # Admin no pharmacy link
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("admin1234")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"✓ Admin user olusturuldu: {admin_user.username}"))
            self.stdout.write(f"  Sifre: admin1234")
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Admin user zaten var: {admin_user.username}"))

        # 5. Eczaci user olustur
        self.stdout.write("Step 5: Eczaci kullanicisi olusturuyorum...")
        pharmacist_user, created = Kullanici.objects.get_or_create(
            username="eczane1",
            defaults={
                "email": "eczaci@demo.local",
                "first_name": "Demo",
                "last_name": "Eczacı",
                "rol": Kullanici.Rol.ECZACI,
                "eczane": eczane,
                "is_staff": False,
                "is_superuser": False,
            }
        )
        if created:
            pharmacist_user.set_password("eczane1234")
            pharmacist_user.save()
            self.stdout.write(self.style.SUCCESS(f"✓ Eczaci user olusturuldu: {pharmacist_user.username}"))
            self.stdout.write(f"  Sifre: eczane1234")
            self.stdout.write(f"  Eczane: {eczane.ad}")
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Eczaci user zaten var: {pharmacist_user.username}"))

        self.stdout.write(self.style.SUCCESS("\n=== DEV SEED TAMAMLANDI ===\n"))
        self.stdout.write("DEV CREDENTIALS:")
        self.stdout.write("├─ Admin User: admin / admin1234")
        self.stdout.write("├─ Pharmacist User: eczane1 / eczane1234")
        self.stdout.write("├─ Pharmacy: Demo Eczanesi")
        self.stdout.write("├─ Kiosk MAC: 00:11:22:33:44:55")
        self.stdout.write("└─ Kiosk App Key: demo_kiosk_key_12345")
