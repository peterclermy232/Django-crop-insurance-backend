import logging

from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from insurance.public_ids import id_lookup
from insurance.models import Claim, Farmer
from insurance.models.inspection import ClaimPhoto, Inspection, InspectionPhoto

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {'image/jpeg', 'image/jpg', 'image/png'}

# entity_type -> (model, path from the entity to its organisation id)
ENTITY_TYPES = {
    'farmer': (Farmer, 'organisation_id'),
    'claim': (Claim, 'farmer__organisation_id'),
    'inspection': (Inspection, 'farm__farmer__organisation_id'),
}


class MediaUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > MAX_UPLOAD_BYTES:
            return Response({'error': 'File too large (max 10MB)'}, status=status.HTTP_400_BAD_REQUEST)
        if upload.content_type not in ALLOWED_TYPES:
            return Response({'error': 'Invalid file type (JPEG/PNG only)'}, status=status.HTTP_400_BAD_REQUEST)

        entity_type = request.data.get('entity_type')
        if entity_type not in ENTITY_TYPES:
            return Response({'error': 'entity_type must be farmer, claim or inspection'},
                            status=status.HTTP_400_BAD_REQUEST)

        entity = self._find_entity(entity_type, request)
        if entity is None:
            # The record itself hasn't synced yet; the device retries after the next sync
            return Response({'error': 'Linked record not found. Sync it first.', 'code': 'pending_parent'},
                            status=status.HTTP_409_CONFLICT)

        photo_uuid = request.data.get('client_uuid') or None
        caption = request.data.get('caption', '')[:200]
        latitude = request.data.get('latitude') or None
        longitude = request.data.get('longitude') or None

        with transaction.atomic():
            if entity_type == 'farmer':
                entity.photo.save(upload.name, upload, save=True)
                return Response({'entity_type': entity_type, 'entity_id': entity.pk,
                                 'file_url': request.build_absolute_uri(entity.photo.url)},
                                status=status.HTTP_201_CREATED)

            photo_model, parent_field = (ClaimPhoto, 'claim') if entity_type == 'claim' \
                else (InspectionPhoto, 'inspection')
            if photo_uuid:
                existing = photo_model.objects.filter(client_uuid=photo_uuid).first()
                if existing is not None:
                    return Response(self._photo_payload(request, entity_type, entity, existing),
                                    status=status.HTTP_200_OK)
            photo = photo_model(**{parent_field: entity}, client_uuid=photo_uuid, caption=caption,
                                latitude=latitude, longitude=longitude)
            photo.photo.save(upload.name, upload, save=True)

        return Response(self._photo_payload(request, entity_type, entity, photo),
                        status=status.HTTP_201_CREATED)

    @staticmethod
    def _find_entity(entity_type, request):
        model, org_path = ENTITY_TYPES[entity_type]
        entity_uuid = request.data.get('entity_uuid')
        entity_id = request.data.get('entity_id')
        if entity_uuid:
            lookup = {'client_uuid': entity_uuid}
        elif entity_id:
            lookup = id_lookup(model, entity_id)
            if lookup is None:
                return None
        else:
            return None
        return model.objects.filter(**lookup, **{org_path: request.user.organisation_id}).first()

    @staticmethod
    def _photo_payload(request, entity_type, entity, photo):
        return {
            'entity_type': entity_type,
            'entity_id': entity.pk,
            'photo_id': photo.pk,
            'client_uuid': str(photo.client_uuid) if photo.client_uuid else None,
            'file_url': request.build_absolute_uri(photo.photo.url),
        }

    def get(self, request):
        """Photo counts for the current user's organisation."""
        org_id = request.user.organisation_id
        claim_photos = ClaimPhoto.objects.filter(claim__farmer__organisation_id=org_id).count()
        inspection_photos = InspectionPhoto.objects.filter(
            inspection__farm__farmer__organisation_id=org_id).count()
        return Response({
            'claim_photos': claim_photos,
            'inspection_photos': inspection_photos,
            'total': claim_photos + inspection_photos,
        })
