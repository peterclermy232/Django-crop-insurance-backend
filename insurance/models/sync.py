from django.conf import settings
from django.db import models


class SyncTrackedModel(models.Model):
    """
    Fields that let the mobile app work offline.

    - client_uuid: generated on the device when a record is captured, so an
      upload that is retried after a dropped connection updates the same row
      instead of creating a duplicate.
    - updated_at: lets devices download only what changed since their last sync.
    - created_by: the field officer who captured the record.
    """

    client_uuid = models.UUIDField(null=True, blank=True, unique=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        editable=False,
    )

    class Meta:
        abstract = True
