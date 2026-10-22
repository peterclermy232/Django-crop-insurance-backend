"""
Keeps uploaded files (farmer, claim and inspection photos) in the database
instead of on the server's disk, which is wiped on every deploy.

Files are served by StoredFileView. Their URLs carry a signature so they can't
be guessed, while still working in <img> tags that can't send a login token.
"""
import mimetypes

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.core.signing import Signer
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.deconstruct import deconstructible
from django.utils.http import urlencode

_signer = Signer(salt='insurance.stored-file')


def file_signature(name):
    return _signer.signature(name)


def valid_signature(name, signature):
    return bool(signature) and constant_time_compare(file_signature(name), signature)


@deconstructible
class DatabaseStorage(Storage):
    @staticmethod
    def _files():
        from insurance.models import StoredFile
        return StoredFile.objects

    def _open(self, name, mode='rb'):
        content = self._files().filter(name=name).values_list('content', flat=True).first()
        if content is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(content), name=name)

    def _save(self, name, content):
        if hasattr(content, 'seek'):
            content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode()
        content_type = (getattr(content, 'content_type', None)
                        or mimetypes.guess_type(name)[0] or 'application/octet-stream')
        self._files().create(name=name, content=data, size=len(data), content_type=content_type)
        return name

    def exists(self, name):
        return self._files().filter(name=name).exists()

    def delete(self, name):
        self._files().filter(name=name).delete()

    def size(self, name):
        size = self._files().filter(name=name).values_list('size', flat=True).first()
        if size is None:
            raise FileNotFoundError(name)
        return size

    def url(self, name):
        return f"{reverse('stored-file', args=[name])}?{urlencode({'sig': file_signature(name)})}"

    def get_created_time(self, name):
        created = self._files().filter(name=name).values_list('created_at', flat=True).first()
        if created is None:
            raise FileNotFoundError(name)
        return created

    get_modified_time = get_created_time

    def listdir(self, path):
        prefix = f"{path.rstrip('/')}/" if path else ''
        dirs, files = set(), []
        for name in self._files().filter(name__startswith=prefix).values_list('name', flat=True):
            rest = name[len(prefix):]
            if '/' in rest:
                dirs.add(rest.split('/', 1)[0])
            else:
                files.append(rest)
        return sorted(dirs), files
