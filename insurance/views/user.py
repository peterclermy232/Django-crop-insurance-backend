from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status

from insurance.models import User, Organization, Country
from insurance.serializers import (
    UserSerializer,
    OrganizationSerializer,
    CountrySerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return users with related organizations and countries"""
        users = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(
            Organization.objects.filter(organisation_is_deleted=False),
            many=True
        ).data
        countries = CountrySerializer(
            Country.objects.filter(country_is_deleted=False),
            many=True
        ).data

        return Response({
            'usersResponse': users,
            'orgsResponse': orgs,
            'countriesResponse': countries
        })

    @action(detail=False, methods=['post'])
    def login(self, request):
        """DEPRECATED: Use /auth/login/ instead"""
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
                    return Response(
                        {'error': 'User account is inactive'},
                        status=status.HTTP_403_FORBIDDEN
                    )
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