from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from datetime import datetime


class MediaUploadView(APIView):
    """
    Enhanced media upload endpoint for mobile app
    Supports claims photos, inspection photos, and farmer registration photos
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        Upload media file with metadata

        Expected fields:
        - file: The image file
        - entity_type: 'claim' | 'inspection' | 'farmer'
        - entity_id: ID of the related entity (optional for new records)
        - caption: Optional description
        - latitude: Optional GPS latitude
        - longitude: Optional GPS longitude
        """
        try:
            # Validate required fields
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file = request.FILES['file']
            entity_type = request.data.get('entity_type', 'general')
            entity_id = request.data.get('entity_id')
            caption = request.data.get('caption', '')
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')

            # Validate file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                return Response(
                    {'error': 'File too large (max 10MB)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            if file.content_type not in allowed_types:
                return Response(
                    {'error': 'Invalid file type (JPEG/PNG only)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = os.path.splitext(file.name)[1]
            filename = f"{entity_type}_{timestamp}_{request.user.user_id}{ext}"

            # Determine upload path based on entity type
            if entity_type == 'claim':
                upload_path = f'mobile_uploads/claims/{filename}'
            elif entity_type == 'inspection':
                upload_path = f'mobile_uploads/inspections/{filename}'
            elif entity_type == 'farmer':
                upload_path = f'mobile_uploads/farmers/{filename}'
            else:
                upload_path = f'mobile_uploads/general/{filename}'

            # Save file
            file_path = default_storage.save(upload_path, ContentFile(file.read()))
            file_url = default_storage.url(file_path)

            # Build response
            response_data = {
                'success': True,
                'message': 'File uploaded successfully',
                'file_url': request.build_absolute_uri(file_url),
                'file_path': file_path,
                'filename': filename,
                'entity_type': entity_type,
            }

            if entity_id:
                response_data['entity_id'] = entity_id
            if caption:
                response_data['caption'] = caption
            if latitude:
                response_data['latitude'] = latitude
            if longitude:
                response_data['longitude'] = longitude

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {
                    'error': 'Upload failed',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """Get upload statistics for current user"""
        try:
            from insurance.models.inspection import ClaimPhoto, InspectionPhoto

            claim_photos_count = ClaimPhoto.objects.filter(
                claim__farmer__organisation=request.user.organisation
            ).count()

            inspection_photos_count = InspectionPhoto.objects.filter(
                inspection__farm__farmer__organisation=request.user.organisation
            ).count()

            return Response({
                'claim_photos': claim_photos_count,
                'inspection_photos': inspection_photos_count,
                'total': claim_photos_count + inspection_photos_count,
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )