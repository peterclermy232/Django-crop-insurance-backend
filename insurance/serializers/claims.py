from rest_framework import serializers
from django.utils import timezone
import json
from insurance.models import Claim, ClaimAssignment, LossAssessor
from rest_framework.decorators import action


class LossAssessorSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.user_name', read_only=True)
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )

    class Meta:
        model = LossAssessor
        fields = '__all__'


class ClaimSerializer(serializers.ModelSerializer):
    farmer_name = serializers.SerializerMethodField()
    policy_number = serializers.CharField(
        source='quotation.policy_number',
        read_only=True
    )
    assessor_name = serializers.SerializerMethodField()
    loss_details = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Claim
        fields = '__all__'
        read_only_fields = ('claim_id', 'claim_date', 'approval_date')

    def get_farmer_name(self, obj):
        """Return full farmer name"""
        if obj.farmer:
            return f"{obj.farmer.first_name} {obj.farmer.last_name}"
        return None

    def get_assessor_name(self, obj):
        """Return assessor name if assigned"""
        if obj.loss_assessor:
            return obj.loss_assessor.user.user_name
        return None

    def validate_loss_details(self, value):
        """Validate loss_details JSON field"""
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            if not value.strip():
                return None
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise serializers.ValidationError(
                        'loss_details must be a JSON object (dictionary)'
                    )
                return parsed
            except json.JSONDecodeError as e:
                raise serializers.ValidationError(f'Invalid JSON format: {str(e)}')

        raise serializers.ValidationError(
            'loss_details must be a valid JSON object or dictionary'
        )

    def validate_farmer(self, value):
        """Validate farmer exists and is active"""
        if value and value.status != 'ACTIVE':
            raise serializers.ValidationError('Selected farmer is not active')
        return value

    def validate_quotation(self, value):
        """Validate quotation is a written policy"""
        if value:
            # Accept both WRITTEN and PAID status for claims
            if value.status not in ['WRITTEN', 'PAID']:
                raise serializers.ValidationError(
                    f'Can only create claims for written or paid policies. Current status: {value.status}'
                )
            if not value.policy_number:
                raise serializers.ValidationError('Quotation must have a policy number')
        return value

    def validate_estimated_loss_amount(self, value):
        """Validate estimated loss amount"""
        if value <= 0:
            raise serializers.ValidationError('Estimated loss must be greater than zero')
        return value

    def validate_claim_number(self, value):
        """Validate claim number uniqueness"""
        if value:
            existing = Claim.objects.filter(claim_number=value)
            if self.instance:
                existing = existing.exclude(claim_id=self.instance.claim_id)
            if existing.exists():
                raise serializers.ValidationError('A claim with this number already exists')
        return value

    def validate(self, data):
        """Cross-field validation"""
        estimated_loss = data.get('estimated_loss_amount')
        quotation = data.get('quotation')

        if estimated_loss and quotation:
            if estimated_loss > quotation.sum_insured:
                raise serializers.ValidationError({
                    'estimated_loss_amount': f'Estimated loss ({estimated_loss}) cannot exceed sum insured ({quotation.sum_insured})'
                })

        return data

    def create(self, validated_data):
        """Override create to auto-generate claim number if not provided"""
        if not validated_data.get('claim_number'):
            date_str = timezone.now().strftime('%Y%m%d')
            last_claim = Claim.objects.filter(
                claim_number__startswith=f'CLM-{date_str}'
            ).order_by('-claim_id').first()

            if last_claim:
                try:
                    last_num = int(last_claim.claim_number.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            validated_data['claim_number'] = f'CLM-{date_str}-{new_num:06d}'

        if 'loss_details' not in validated_data or validated_data['loss_details'] is None:
            validated_data['loss_details'] = {}

        return super().create(validated_data)

    def to_representation(self, instance):
        """Customize output representation"""
        data = super().to_representation(instance)
        if data.get('loss_details') is None:
            data['loss_details'] = {}
        return data


class ClaimAssignmentSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    assessor_name = serializers.CharField(
        source='loss_assessor.user.user_name',
        read_only=True
    )

    class Meta:
        model = ClaimAssignment
        fields = '__all__'


@action(detail=True, methods=['post'])
def upload_photo(self, request, pk=None):
    """Upload photo for claim"""
    claim = self.get_object()
    photo = request.FILES.get('photo')

    if not photo:
        return Response(
            {'error': 'No photo provided'},
            status=http_status.HTTP_400_BAD_REQUEST
        )

    from insurance.models.inspection import ClaimPhoto

    claim_photo = ClaimPhoto.objects.create(
        claim=claim,
        photo=photo,
        caption=request.data.get('caption', ''),
        latitude=request.data.get('latitude'),
        longitude=request.data.get('longitude')
    )

    return Response({
        'photo_url': request.build_absolute_uri(claim_photo.photo.url),
        'photo_id': claim_photo.photo_id,
        'message': 'Photo uploaded successfully'
    }, status=http_status.HTTP_201_CREATED)


@action(detail=True, methods=['get'])
def photos(self, request, pk=None):
    """Get all photos for a claim"""
    claim = self.get_object()
    from insurance.models.inspection import ClaimPhoto
    from insurance.serializers.inspection import ClaimPhotoSerializer

    photos = ClaimPhoto.objects.filter(claim=claim)
    serializer = ClaimPhotoSerializer(photos, many=True, context={'request': request})
    return Response(serializer.data)
