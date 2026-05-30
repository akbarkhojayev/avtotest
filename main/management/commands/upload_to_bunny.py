import os
import requests as http
from django.conf import settings
from django.core.management.base import BaseCommand
from main.models import Video


class Command(BaseCommand):
    help = "Mahalliy video fayllarni BunnyCDN ga yuklaydi"

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        access_key = settings.BUNNY_ACCESS_KEY
        storage_zone = settings.BUNNY_STORAGE_ZONE
        base_url = f"https://storage.bunnycdn.com/{storage_zone}/"

        videos = Video.objects.exclude(video_file='').exclude(video_file=None)
        total = videos.count()

        if total == 0:
            self.stdout.write("Yuklanadigan video topilmadi.")
            return

        self.stdout.write(f"{total} ta video topildi.\n")
        success, skipped, failed = 0, 0, 0

        for video in videos:
            name = str(video.video_file.name)
            local_path = os.path.join(media_root, name)

            if not os.path.exists(local_path):
                self.stdout.write(self.style.WARNING(f"  SKIP (mahalliy fayl yo'q): {name}"))
                skipped += 1
                continue

            bunny_url = base_url + name
            # Avval BunnyCDN da borligini tekshir
            check = http.head(bunny_url, headers={'AccessKey': access_key})
            if check.status_code == 200:
                self.stdout.write(f"  SKIP (CDN da bor): {name}")
                skipped += 1
                continue

            # Yuklash
            with open(local_path, 'rb') as f:
                resp = http.put(
                    bunny_url,
                    data=f,
                    headers={
                        'AccessKey': access_key,
                        'Content-Type': 'application/octet-stream',
                    },
                )

            if resp.status_code in (200, 201):
                self.stdout.write(self.style.SUCCESS(f"  OK: {name}"))
                success += 1
            else:
                self.stdout.write(self.style.ERROR(f"  XATO ({resp.status_code}): {name}"))
                failed += 1

        self.stdout.write(f"\nNatija: {success} yuklandi, {skipped} o'tkazib yuborildi, {failed} xato.")
