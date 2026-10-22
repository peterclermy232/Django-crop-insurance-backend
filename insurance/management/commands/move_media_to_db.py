"""Copies files uploaded before DatabaseStorage from MEDIA_ROOT into the database."""
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from insurance.models import StoredFile
from insurance.models.farmer import Farmer
from insurance.models.inspection import ClaimPhoto, InspectionPhoto


class Command(BaseCommand):
    help = 'Copy photos referenced by farmers, claims and inspections from MEDIA_ROOT into the database.'

    def handle(self, *args, **options):
        root = Path(settings.MEDIA_ROOT)
        copied = skipped = missing = 0
        for model in (Farmer, ClaimPhoto, InspectionPhoto):
            names = model.objects.exclude(photo='').exclude(photo__isnull=True).values_list('photo', flat=True)
            for name in names:
                if StoredFile.objects.filter(name=name).exists():
                    skipped += 1
                    continue
                path = root / name
                if not path.is_file():
                    missing += 1
                    self.stderr.write(f'Missing on disk: {name}')
                    continue
                data = path.read_bytes()
                StoredFile.objects.create(
                    name=name, content=data, size=len(data),
                    content_type=mimetypes.guess_type(name)[0] or 'application/octet-stream')
                copied += 1
        self.stdout.write(self.style.SUCCESS(
            f'Copied {copied}, already in database {skipped}, missing on disk {missing}.'))
