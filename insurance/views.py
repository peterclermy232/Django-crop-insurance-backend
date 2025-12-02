from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from datetime import datetime, timedelta
from .models import *
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import WeatherData
from .serializers import WeatherDataSerializer
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max, Min, Sum


# ============== AUTHENTICATION VIEWS ==============

class LoginView(APIView):
    """User login endpoint that returns JWT tokens"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Try to get user by email OR username
            try:
                user = User.objects.get(user_email=username)
            except User.DoesNotExist:
                # Try by user_name if email doesn't work
                user = User.objects.get(user_name=username)

            # Check if password is hashed or plain text
            password_valid = False

            # First try with hashed password (proper way)
            if user.check_password(password):
                password_valid = True
            # If that fails, check if it's a plain text password (temporary fix)
            elif user.password == password:
                password_valid = True
                # IMPORTANT: Hash the password for future logins
                user.set_password(password)
                user.save(update_fields=['password'])
                print(f"Password hashed for user: {user.user_email}")

            if password_valid:
                # Check if user is active
                if user.user_status != 'ACTIVE':
                    return Response(
                        {'error': 'User account is inactive'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)

                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])

                return Response({
                    'token': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                    'expires_in': 3600  # 1 hour in seconds
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            print(f"Login error: {str(e)}")
            return Response(
                {'error': f'Login failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegisterView(APIView):
    """User registration endpoint"""
    permission_classes = [AllowAny]

    def post(self, request):
        # Extract registration data
        email = request.data.get('user_email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        phone = request.data.get('user_phone_number')
        organisation_id = request.data.get('organisation_id')

        # Validation
        if not all([email, password, first_name, last_name]):
            return Response(
                {'error': 'Email, password, first name, and last name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already exists
        if User.objects.filter(user_email=email).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create new user
            user = User.objects.create(
                user_email=email,
                first_name=first_name,
                last_name=last_name,
                user_phone_number=phone,
                organisation_id=organisation_id,
                user_status='ACTIVE',
                user_role='USER',  # Default role
                user_is_active=True
            )

            # Set password (this hashes it)
            user.set_password(password)
            user.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'User registered successfully',
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Registration failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """User logout endpoint - blacklists the refresh token"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Logout failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RefreshTokenView(APIView):
    """Refresh access token using refresh token"""
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create RefreshToken instance
            refresh = RefreshToken(refresh_token)

            # Generate new access token
            access_token = str(refresh.access_token)

            return Response({
                'token': access_token,
                'expires_in': 3600  # 1 hour in seconds
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


# ============== EXISTING VIEWSETS ==============

class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.filter(country_is_deleted=False)
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class OrganizationTypeViewSet(viewsets.ModelViewSet):
    queryset = OrganizationType.objects.all()
    serializer_class = OrganizationTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('all') == 'true':
            return queryset
        return queryset[:10]


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.
    Provides CRUD operations: list, retrieve, create, update, partial_update, destroy
    """
    queryset = Organization.objects.filter(organisation_is_deleted=False)
    serializer_class = OrganizationSerializer
    lookup_field = 'organisation_id'

    def get_permissions(self):
        """
        Allow unauthenticated access to list and retrieve operations
        Require authentication for create, update, and delete operations
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Custom action to get organizations with additional details"""
        organisations = self.get_queryset()
        serializer = self.get_serializer(organisations, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Override to add custom logic on update"""
        serializer.save(
            modified_by=self.request.user.user_id,
            latest_ip=self.request.META.get('REMOTE_ADDR')
        )

    def perform_create(self, serializer):
        """Override to add custom logic on create"""
        serializer.save(
            added_by=self.request.user.user_id,
            source_ip=self.request.META.get('REMOTE_ADDR')
        )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return users with related organizations and countries"""
        users = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data
        countries = CountrySerializer(Country.objects.filter(country_is_deleted=False), many=True).data

        return Response({
            'usersResponse': users,
            'orgsResponse': orgs,
            'countriesResponse': countries
        })

    # DEPRECATED: Use LoginView instead
    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login endpoint - DEPRECATED: Use /auth/login/ instead"""
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(user_email=username)
            if user.check_password(password):
                if user.user_status == 'ACTIVE':
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'token': str(refresh.access_token),
                        'refresh': str(refresh),
                        'user': self.get_serializer(user).data
                    })
                else:
                    return Response({'error': 'User account is inactive'},
                                    status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': 'Invalid credentials'},
                                status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'},
                            status=status.HTTP_401_UNAUTHORIZED)


class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.filter(deleted=False)
    serializer_class = CropSerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return crops with organizations"""
        crops = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data

        return Response({
            'cropsResponse': crops,
            'orgsResponse': {'results': orgs}
        })


class CropVarietyViewSet(viewsets.ModelViewSet):
    queryset = CropVariety.objects.filter(deleted=False)
    serializer_class = CropVarietySerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return crop varieties with crops and organizations"""
        varieties = self.get_serializer(self.get_queryset(), many=True).data
        crops = CropSerializer(Crop.objects.filter(deleted=False), many=True).data
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data

        return Response({
            'cropVarResponse': varieties,
            'cropsResponse': crops,
            'orgsResponse': {'results': orgs}
        })


class CoverTypeViewSet(viewsets.ModelViewSet):
    queryset = CoverType.objects.filter(deleted=False)
    serializer_class = CoverTypeSerializer


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.filter(deleted=False)
    serializer_class = ProductCategorySerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return product categories with cover types and organizations"""
        categories = self.get_serializer(self.get_queryset(), many=True).data
        cover_types = CoverTypeSerializer(CoverType.objects.filter(deleted=False), many=True).data
        orgs = OrganizationSerializer(Organization.objects.filter(organisation_is_deleted=False), many=True).data

        return Response({
            'productCategoryResponse': categories,
            'coverTypesResponse': cover_types,
            'organisationsResponse': orgs
        })


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.filter(deleted=False)
    serializer_class = SeasonSerializer


class FarmerViewSet(viewsets.ModelViewSet):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(id_number__icontains=search) |
                Q(phone_number__icontains=search)
            )
        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get farmer statistics"""
        total = self.get_queryset().count()
        active = self.get_queryset().filter(status='ACTIVE').count()
        by_gender = self.get_queryset().values('gender').annotate(count=Count('farmer_id'))

        return Response({
            'total_farmers': total,
            'active_farmers': active,
            'by_gender': list(by_gender)
        })


class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.all()
    serializer_class = FarmSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        farmer_id = self.request.query_params.get('farmer_id')
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)
        return queryset


class InsuranceProductViewSet(viewsets.ModelViewSet):
    queryset = InsuranceProduct.objects.all()
    serializer_class = InsuranceProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


# views.py - FIXED QuotationViewSet

class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.select_related(
        'farmer', 'farm', 'insurance_product'
    ).all()
    serializer_class = QuotationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        farmer_id = self.request.query_params.get('farmer_id')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create quotation with detailed error handling"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e), 'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': f'Error creating quotation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update quotation with detailed error handling"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e), 'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': f'Error updating quotation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get quotation statistics"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(count=Count('quotation_id'))
        total_premium = self.get_queryset().aggregate(total=Sum('premium_amount'))['total'] or 0

        return Response({
            'total_quotations': total,
            'by_status': list(by_status),
            'total_premium': float(total_premium)
        })

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark quotation as paid"""
        try:
            quotation = self.get_object()

            if quotation.status == 'PAID':
                return Response(
                    {'error': 'Quotation is already marked as paid'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment_reference = request.data.get('payment_reference')
            if not payment_reference:
                return Response(
                    {'error': 'Payment reference is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            quotation.status = 'PAID'
            quotation.payment_date = timezone.now()
            quotation.payment_reference = payment_reference
            quotation.save()

            return Response(self.get_serializer(quotation).data)
        except Exception as e:
            return Response(
                {'error': f'Failed to mark as paid: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def write_policy(self, request, pk=None):
        """Convert quotation to written policy"""
        try:
            quotation = self.get_object()

            if quotation.status != 'PAID':
                return Response(
                    {'error': 'Quotation must be paid before writing policy'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if quotation.policy_number:
                return Response(
                    {'error': 'Policy already written',
                     'policy_number': quotation.policy_number},
                    status=status.HTTP_400_BAD_REQUEST
                )

            quotation.status = 'WRITTEN'
            quotation.policy_number = f"POL-{timezone.now().strftime('%Y%m%d')}-{quotation.quotation_id}"
            quotation.save()

            return Response({
                'message': 'Policy written successfully',
                'policy_number': quotation.policy_number,
                'quotation': self.get_serializer(quotation).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to write policy: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return quotations with related data for frontend"""
        quotations = self.get_serializer(self.get_queryset(), many=True).data
        farmers = FarmerSerializer(Farmer.objects.all(), many=True).data
        products = InsuranceProductSerializer(
            InsuranceProduct.objects.filter(status='ACTIVE'),
            many=True
        ).data

        return Response({
            'quotations': quotations,
            'farmers': farmers,
            'insurance_products': products
        })


class LossAssessorViewSet(viewsets.ModelViewSet):
    queryset = LossAssessor.objects.all()
    serializer_class = LossAssessorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class ClaimViewSet(viewsets.ModelViewSet):
    queryset = Claim.objects.all()
    serializer_class = ClaimSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        farmer_id = self.request.query_params.get('farmer_id')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if farmer_id:
            queryset = queryset.filter(farmer_id=farmer_id)

        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get claim statistics"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(count=Count('claim_id'))
        total_claimed = self.get_queryset().aggregate(total=Sum('estimated_loss_amount'))['total'] or 0
        total_approved = self.get_queryset().aggregate(total=Sum('approved_amount'))['total'] or 0

        return Response({
            'total_claims': total,
            'by_status': list(by_status),
            'total_claimed': float(total_claimed),
            'total_approved': float(total_approved)
        })

    @action(detail=True, methods=['post'])
    def assign_assessor(self, request, pk=None):
        """Assign loss assessor to claim"""
        claim = self.get_object()
        assessor_id = request.data.get('assessor_id')

        if not assessor_id:
            return Response({'error': 'Assessor ID required'},
                            status=status.HTTP_400_BAD_REQUEST)

        ClaimAssignment.objects.create(
            claim=claim,
            loss_assessor_id=assessor_id,
            assigned_by=request.user.user_id if hasattr(request.user, 'user_id') else 1
        )

        claim.status = 'UNDER_ASSESSMENT'
        claim.loss_assessor_id = assessor_id
        claim.save()

        return Response(self.get_serializer(claim).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve claim"""
        claim = self.get_object()
        claim.status = 'PENDING_PAYMENT'
        claim.approved_amount = request.data.get('approved_amount')
        claim.approval_date = timezone.now()
        claim.save()

        return Response(self.get_serializer(claim).data)


class SubsidyViewSet(viewsets.ModelViewSet):
    queryset = Subsidy.objects.all()
    serializer_class = SubsidySerializer


# Add to views.py - Updated InvoiceViewSet with all settlement features

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        organisation_id = self.request.query_params.get('organisation_id')

        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        if organisation_id:
            queryset = queryset.filter(organisation_id=organisation_id)

        return queryset.order_by('-date_time_added')

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get invoice statistics by status"""
        total = self.get_queryset().count()
        by_status = self.get_queryset().values('status').annotate(count=Count('invoice_id'))

        total_amount = self.get_queryset().aggregate(
            total=Sum('amount')
        )['total'] or 0

        approved_amount = self.get_queryset().filter(
            status='APPROVED'
        ).aggregate(total=Sum('amount'))['total'] or 0

        settled_amount = self.get_queryset().filter(
            status='SETTLED'
        ).aggregate(total=Sum('amount'))['total'] or 0

        pending_amount = self.get_queryset().filter(
            status='PENDING'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_invoices': total,
            'by_status': list(by_status),
            'total_amount': float(total_amount),
            'approved_amount': float(approved_amount),
            'settled_amount': float(settled_amount),
            'pending_amount': float(pending_amount)
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve invoice - moves from PENDING to APPROVED"""
        try:
            invoice = self.get_object()

            if invoice.status != 'PENDING':
                return Response(
                    {'error': 'Only pending invoices can be approved'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invoice.status = 'APPROVED'
            invoice.approved_date = timezone.now()
            invoice.save()

            return Response({
                'message': 'Invoice approved successfully',
                'invoice': self.get_serializer(invoice).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to approve invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        """Settle invoice - moves from APPROVED to SETTLED"""
        try:
            invoice = self.get_object()

            if invoice.status != 'APPROVED':
                return Response(
                    {'error': 'Only approved invoices can be settled'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment_reference = request.data.get('payment_reference')
            if not payment_reference:
                return Response(
                    {'error': 'Payment reference is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            invoice.status = 'SETTLED'
            invoice.settlement_date = timezone.now()
            invoice.payment_reference = payment_reference
            invoice.save()

            return Response({
                'message': 'Invoice settled successfully',
                'invoice': self.get_serializer(invoice).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to settle invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject invoice - moves to REJECTED status"""
        try:
            invoice = self.get_object()

            if invoice.status not in ['PENDING', 'APPROVED']:
                return Response(
                    {'error': 'Cannot reject settled invoices'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            rejection_reason = request.data.get('rejection_reason', '')

            invoice.status = 'REJECTED'
            invoice.payment_reference = f"REJECTED: {rejection_reason}"
            invoice.save()

            return Response({
                'message': 'Invoice rejected successfully',
                'invoice': self.get_serializer(invoice).data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to reject invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending invoices"""
        invoices = self.get_queryset().filter(status='PENDING')
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def approved(self, request):
        """Get all approved invoices (ready for settlement)"""
        invoices = self.get_queryset().filter(status='APPROVED')
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def settled(self, request):
        """Get all settled invoices"""
        invoices = self.get_queryset().filter(status='SETTLED')
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """Approve multiple invoices at once"""
        invoice_ids = request.data.get('invoice_ids', [])

        if not invoice_ids:
            return Response(
                {'error': 'No invoice IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = Invoice.objects.filter(
            invoice_id__in=invoice_ids,
            status='PENDING'
        )

        count = invoices.update(
            status='APPROVED',
            approved_date=timezone.now()
        )

        return Response({
            'message': f'{count} invoices approved successfully',
            'count': count
        })

    @action(detail=False, methods=['post'])
    def bulk_settle(self, request):
        """Settle multiple invoices at once"""
        invoice_ids = request.data.get('invoice_ids', [])
        payment_reference = request.data.get('payment_reference')

        if not invoice_ids:
            return Response(
                {'error': 'No invoice IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not payment_reference:
            return Response(
                {'error': 'Payment reference is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoices = Invoice.objects.filter(
            invoice_id__in=invoice_ids,
            status='APPROVED'
        )

        count = invoices.update(
            status='SETTLED',
            settlement_date=timezone.now(),
            payment_reference=payment_reference
        )

        return Response({
            'message': f'{count} invoices settled successfully',
            'count': count
        })


class AdvisoryViewSet(viewsets.ModelViewSet):
    queryset = Advisory.objects.all()
    serializer_class = AdvisorySerializer

    @action(detail=False, methods=['post'])
    def send_advisory(self, request):
        """Send advisory message"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            advisory = serializer.save()

            if advisory.send_now:
                advisory.status = 'SENT'
                advisory.sent_date_time = timezone.now()
            else:
                advisory.status = 'SCHEDULED'

            advisory.save()

            return Response(self.get_serializer(advisory).data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def estimate_recipients(self, request):
        """Estimate number of recipients for advisory"""
        province = request.data.get('province')
        district = request.data.get('district')
        sector = request.data.get('sector')
        gender = request.data.get('gender')
        policy_status = request.data.get('policyStatus')

        farmers = Farmer.objects.all()

        if province:
            farmers = farmers.filter(farms__location_province=province)
        if district:
            farmers = farmers.filter(farms__location_district=district)
        if sector:
            farmers = farmers.filter(farms__location_sector=sector)
        if gender and gender != 'All':
            farmers = farmers.filter(gender=gender)

        count = farmers.distinct().count()

        return Response({'count': count})


class WeatherDataViewSet(viewsets.ModelViewSet):
    queryset = WeatherData.objects.all()
    serializer_class = WeatherDataSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        data_type = self.request.query_params.get('type')
        if data_type:
            queryset = queryset.filter(data_type=data_type)
        return queryset


class DashboardViewSet(viewsets.ViewSet):
    """Dashboard statistics endpoint"""

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall dashboard statistics"""
        today = timezone.now().date()

        # Farmer statistics
        total_farmers = Farmer.objects.count()
        active_farmers = Farmer.objects.filter(status='ACTIVE').count()

        # Quotation statistics
        total_quotations = Quotation.objects.count()
        open_quotations = Quotation.objects.filter(status='OPEN').count()
        paid_quotations = Quotation.objects.filter(status='PAID').count()
        written_policies = Quotation.objects.filter(status='WRITTEN').count()

        # Claim statistics
        total_claims = Claim.objects.count()
        open_claims = Claim.objects.filter(status='OPEN').count()
        pending_payment_claims = Claim.objects.filter(status='PENDING_PAYMENT').count()
        paid_claims = Claim.objects.filter(status='PAID').count()

        # Financial statistics
        total_premium = Quotation.objects.aggregate(total=Sum('premium_amount'))['total'] or 0
        total_claims_value = Claim.objects.aggregate(total=Sum('approved_amount'))['total'] or 0

        return Response({
            'farmers': {
                'total': total_farmers,
                'active': active_farmers
            },
            'quotations': {
                'total': total_quotations,
                'open': open_quotations,
                'paid': paid_quotations,
                'written': written_policies
            },
            'claims': {
                'total': total_claims,
                'open': open_claims,
                'pending_payment': pending_payment_claims,
                'paid': paid_claims
            },
            'financials': {
                'total_premium': float(total_premium),
                'total_claims_value': float(total_claims_value)
            }
        })

    class WeatherDataViewSet(viewsets.ModelViewSet):
        """
        ViewSet for managing weather data (historical and forecast)
        """
        queryset = WeatherData.objects.all()
        serializer_class = WeatherDataSerializer

        def get_queryset(self):
            queryset = super().get_queryset()

            # Filter by data type (HISTORICAL or FORECAST)
            data_type = self.request.query_params.get('type')
            if data_type:
                queryset = queryset.filter(data_type=data_type.upper())

            # Filter by location
            location = self.request.query_params.get('location')
            if location:
                queryset = queryset.filter(location__icontains=location)

            # Filter by date range
            start_date = self.request.query_params.get('start_date')
            end_date = self.request.query_params.get('end_date')

            if start_date:
                queryset = queryset.filter(recorded_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(recorded_at__lte=end_date)

            # Order by most recent first
            return queryset.order_by('-recorded_at')

        def create(self, request, *args, **kwargs):
            """
            Create new weather data entry
            """
            # Ensure data_type is uppercase
            data = request.data.copy()
            if 'data_type' in data:
                data['data_type'] = data['data_type'].upper()

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )

        def update(self, request, *args, **kwargs):
            """
            Update weather data entry
            """
            partial = kwargs.pop('partial', False)
            instance = self.get_object()

            data = request.data.copy()
            if 'data_type' in data:
                data['data_type'] = data['data_type'].upper()

            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)

        @action(detail=False, methods=['get'])
        def statistics(self, request):
            """
            Get weather data statistics
            """
            data_type = request.query_params.get('type', 'HISTORICAL')
            location = request.query_params.get('location')

            queryset = self.get_queryset().filter(data_type=data_type.upper())
            if location:
                queryset = queryset.filter(location=location)

            stats = queryset.aggregate(
                total_records=Count('weather_id'),
                avg_value=Avg('value'),
                max_value=Max('value'),
                min_value=Min('value'),
            )

            # Get locations breakdown
            locations = queryset.values('location').annotate(
                count=Count('weather_id'),
                avg_value=Avg('value')
            ).order_by('-count')

            return Response({
                'statistics': stats,
                'by_location': list(locations),
                'data_type': data_type
            })

        @action(detail=False, methods=['get'])
        def historical(self, request):
            """
            Get only historical weather data
            """
            queryset = self.get_queryset().filter(data_type='HISTORICAL')

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        @action(detail=False, methods=['get'])
        def forecast(self, request):
            """
            Get only forecast weather data
            """
            queryset = self.get_queryset().filter(data_type='FORECAST')

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        @action(detail=False, methods=['get'])
        def compare(self, request):
            """
            Compare historical and forecast data
            """
            location = request.query_params.get('location')
            if not location:
                return Response(
                    {'error': 'Location parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get historical data
            historical = WeatherData.objects.filter(
                location=location,
                data_type='HISTORICAL'
            ).aggregate(
                avg_value=Avg('value'),
                max_value=Max('value'),
                min_value=Min('value'),
                count=Count('weather_id')
            )

            # Get forecast data
            forecast = WeatherData.objects.filter(
                location=location,
                data_type='FORECAST'
            ).aggregate(
                avg_value=Avg('value'),
                max_value=Max('value'),
                min_value=Min('value'),
                count=Count('weather_id')
            )

            return Response({
                'location': location,
                'historical': historical,
                'forecast': forecast
            })

        @action(detail=False, methods=['get'])
        def recent(self, request):
            """
            Get recent weather data (last 7 days)
            """
            data_type = request.query_params.get('type')
            days = int(request.query_params.get('days', 7))

            since = datetime.now() - timedelta(days=days)
            queryset = self.get_queryset().filter(recorded_at__gte=since)

            if data_type:
                queryset = queryset.filter(data_type=data_type.upper())

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        @action(detail=False, methods=['delete'])
        def bulk_delete(self, request):
            """
            Bulk delete weather data by IDs
            """
            ids = request.data.get('ids', [])
            if not ids:
                return Response(
                    {'error': 'No IDs provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            deleted_count = WeatherData.objects.filter(
                weather_id__in=ids
            ).delete()[0]

            return Response({
                'message': f'Successfully deleted {deleted_count} records',
                'deleted_count': deleted_count
            })

        @action(detail=False, methods=['post'])
        def bulk_create(self, request):
            """
            Bulk create weather data entries
            """
            data_list = request.data.get('data', [])
            if not data_list:
                return Response(
                    {'error': 'No data provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Ensure all data_types are uppercase
            for item in data_list:
                if 'data_type' in item:
                    item['data_type'] = item['data_type'].upper()

            serializer = self.get_serializer(data=data_list, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            return Response({
                'message': f'Successfully created {len(serializer.data)} records',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
