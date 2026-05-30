import requests
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class BunnyStorage(Storage):
    """
    BunnyCDN Storage Zone uchun Django storage backend.
    Fayllarni BunnyCDN ga yuklaydi va CDN URL qaytaradi.
    """

    def __init__(self):
        self.storage_zone = settings.BUNNY_STORAGE_ZONE
        self.access_key = settings.BUNNY_ACCESS_KEY
        self.cdn_url = settings.BUNNY_CDN_URL.rstrip('/')
        self.base_api = f"https://storage.bunnycdn.com/{self.storage_zone}/"

    def _headers(self):
        return {
            'AccessKey': self.access_key,
            'Content-Type': 'application/octet-stream',
        }

    def _save(self, name, content):
        name = name.replace('\\', '/')
        url = self.base_api + name
        content.seek(0)
        response = requests.put(url, data=content.read(), headers=self._headers())
        response.raise_for_status()
        return name

    def url(self, name):
        return f"{self.cdn_url}/{name}"

    def exists(self, name):
        url = self.base_api + name
        response = requests.get(url, headers={'AccessKey': self.access_key})
        return response.status_code == 200

    def delete(self, name):
        url = self.base_api + name
        requests.delete(url, headers={'AccessKey': self.access_key})

    def size(self, name):
        url = self.base_api + name
        response = requests.get(url, headers={'AccessKey': self.access_key}, stream=True)
        if response.status_code == 200:
            return int(response.headers.get('Content-Length', 0))
        return 0
