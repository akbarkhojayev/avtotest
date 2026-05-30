import hashlib, base64, time
import requests as http
from django.conf import settings
from django.core.management.base import BaseCommand
from main.models import Video


class Command(BaseCommand):
    help = "BunnyCDN ulanishini va token formatini tekshiradi"

    def handle(self, *args, **options):
        token_key = getattr(settings, 'BUNNY_TOKEN_KEY', None)
        cdn_url    = getattr(settings, 'BUNNY_CDN_URL', '').rstrip('/')
        access_key = getattr(settings, 'BUNNY_ACCESS_KEY', '')
        zone       = getattr(settings, 'BUNNY_STORAGE_ZONE', '')

        self.stdout.write("=== BunnyCDN sozlamalari ===")
        self.stdout.write(f"  BUNNY_STORAGE_ZONE : {zone}")
        self.stdout.write(f"  BUNNY_CDN_URL      : {cdn_url}")
        self.stdout.write(f"  BUNNY_ACCESS_KEY   : {access_key[:8]}..." if access_key else "  BUNNY_ACCESS_KEY   : YO'Q!")
        self.stdout.write(f"  BUNNY_TOKEN_KEY    : {token_key[:8]}..." if token_key else "  BUNNY_TOKEN_KEY    : YO'Q!")

        # Birinchi videoni ol
        video = Video.objects.exclude(video_file='').exclude(video_file=None).first()
        if not video:
            self.stdout.write(self.style.ERROR("\nVideo topilmadi."))
            return

        name = str(video.video_file.name)
        path = '/' + name.lstrip('/')
        self.stdout.write(f"\n=== Test video ===")
        self.stdout.write(f"  Nomi   : {video.title}")
        self.stdout.write(f"  Fayl   : {name}")

        # 1. Storage da borligini tekshir
        storage_url = f"https://storage.bunnycdn.com/{zone}/{name}"
        check = http.head(storage_url, headers={'AccessKey': access_key})
        self.stdout.write(f"\n=== Storage tekshiruv ===")
        self.stdout.write(f"  URL    : {storage_url}")
        if check.status_code == 200:
            self.stdout.write(self.style.SUCCESS("  Holat  : TOPILDI ✓"))
        else:
            self.stdout.write(self.style.ERROR(f"  Holat  : TOPILMADI ({check.status_code})"))
            self.stdout.write("  → Avval videoni BunnyCDN ga yuklang: python manage.py upload_to_bunny")
            return

        # 2. Token yasash
        if not token_key:
            self.stdout.write(self.style.ERROR("\nBUNNY_TOKEN_KEY sozlanmagan!"))
            return

        expires = int(time.time()) + 3600
        raw = f"{token_key}{path}{expires}"
        token = base64.b64encode(
            hashlib.md5(raw.encode()).digest()
        ).decode().replace('+', '-').replace('/', '_').rstrip('=')

        signed_url = f"{cdn_url}{path}?token={token}&expires={expires}"
        plain_url  = f"{cdn_url}{path}"

        self.stdout.write(f"\n=== Token tekshiruv ===")
        self.stdout.write(f"  Hash qilindi: {token_key[:8]}...{path}{expires}")
        self.stdout.write(f"  Token       : {token}")

        # Token bilan so'rov
        r_signed = http.head(signed_url)
        self.stdout.write(f"\n  Signed URL natija : {r_signed.status_code}")

        # Token siz so'rov
        r_plain  = http.head(plain_url)
        self.stdout.write(f"  Plain  URL natija : {r_plain.status_code}")

        self.stdout.write(f"\n=== Test URL ===")
        self.stdout.write(f"  {signed_url}")

        if r_signed.status_code == 200:
            self.stdout.write(self.style.SUCCESS("\n✓ BunnyCDN to'g'ri ishlayapti!"))
        elif r_plain.status_code == 200:
            self.stdout.write(self.style.WARNING("\n⚠ Token auth o'chirilgan yoki token noto'g'ri — token siz ham ishlayapti"))
        else:
            self.stdout.write(self.style.ERROR(f"\n✗ Muammo bor. Signed:{r_signed.status_code} Plain:{r_plain.status_code}"))
