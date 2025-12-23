from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime
from django.db import transaction

from insurance.models import Farmer, Farm, Quotation, Claim
from insurance.serializers import (
    FarmerSerializer, FarmSerializer, QuotationSerializer, ClaimSerializer
)


class SyncAPIView(APIView):
    """Bidirectional sync between mobile and backend"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        last_sync = request.data.get('last_sync_timestamp')
        mobile_data = request.data.get('pending_data', {})

        # Parse timestamp
        if last_sync:
            try:
                last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            except ValueError:
                last_sync_dt = datetime.min
        else:
            last_sync_dt = datetime.min

        # Process uploads
        upload_results = self._process_uploads(mobile_data, request.user)

        # Get server updates
        server_updates = self._get_server_updates(last_sync_dt, request.user)

        # Detect conflicts
        conflicts = self._detect_conflicts(mobile_data, server_updates)

        return Response({
            'upload_results': upload_results,
            'server_updates': server_updates,
            'conflicts': conflicts,
            'sync_timestamp': timezone.now().isoformat(),
            'status': 'success'
        })

    @transaction.atomic
    def _process_uploads(self, mobile_data, user):
        """Process data uploaded from mobile"""
        results = {
            'farmers': {'created': 0, 'updated': 0, 'errors': []},
            'farms': {'created': 0, 'updated': 0, 'errors': []},
            'quotations': {'created': 0, 'updated': 0, 'errors': []},
            'claims': {'created': 0, 'updated': 0, 'errors': []},
        }

        # Process farmers
        for farmer_data in mobile_data.get('farmers', []):
            try:
                farmer_id = farmer_data.pop('id', None) or farmer_data.pop('farmer_id', None)

                if farmer_id:
                    farmer = Farmer.objects.get(pk=farmer_id)
                    serializer = FarmerSerializer(farmer, data=farmer_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        results['farmers']['updated'] += 1
                    else:
                        results['farmers']['errors'].append({
                            'id': farmer_id,
                            'errors': serializer.errors
                        })
                else:
                    serializer = FarmerSerializer(data=farmer_data)
                    if serializer.is_valid():
                        serializer.save()
                        results['farmers']['created'] += 1
                    else:
                        results['farmers']['errors'].append({
                            'data': farmer_data,
                            'errors': serializer.errors
                        })
            except Farmer.DoesNotExist:
                results['farmers']['errors'].append({
                    'id': farmer_id,
                    'error': 'Farmer not found'
                })
            except Exception as e:
                results['farmers']['errors'].append({
                    'data': farmer_data,
                    'error': str(e)
                })

        # Process farms
        for farm_data in mobile_data.get('farms', []):
            try:
                farm_id = farm_data.pop('id', None) or farm_data.pop('farm_id', None)

                if farm_id:
                    farm = Farm.objects.get(pk=farm_id)
                    serializer = FarmSerializer(farm, data=farm_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        results['farms']['updated'] += 1
                    else:
                        results['farms']['errors'].append({
                            'id': farm_id,
                            'errors': serializer.errors
                        })
                else:
                    serializer = FarmSerializer(data=farm_data)
                    if serializer.is_valid():
                        serializer.save()
                        results['farms']['created'] += 1
                    else:
                        results['farms']['errors'].append({
                            'data': farm_data,
                            'errors': serializer.errors
                        })
            except Farm.DoesNotExist:
                results['farms']['errors'].append({
                    'id': farm_id,
                    'error': 'Farm not found'
                })
            except Exception as e:
                results['farms']['errors'].append({
                    'data': farm_data,
                    'error': str(e)
                })

        # Process quotations
        for quot_data in mobile_data.get('quotations', []):
            try:
                quot_id = quot_data.pop('id', None) or quot_data.pop('quotation_id', None)

                if quot_id:
                    quotation = Quotation.objects.get(pk=quot_id)
                    serializer = QuotationSerializer(quotation, data=quot_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        results['quotations']['updated'] += 1
                    else:
                        results['quotations']['errors'].append({
                            'id': quot_id,
                            'errors': serializer.errors
                        })
                else:
                    serializer = QuotationSerializer(data=quot_data)
                    if serializer.is_valid():
                        serializer.save()
                        results['quotations']['created'] += 1
                    else:
                        results['quotations']['errors'].append({
                            'data': quot_data,
                            'errors': serializer.errors
                        })
            except Quotation.DoesNotExist:
                results['quotations']['errors'].append({
                    'id': quot_id,
                    'error': 'Quotation not found'
                })
            except Exception as e:
                results['quotations']['errors'].append({
                    'data': quot_data,
                    'error': str(e)
                })

        # Process claims
        for claim_data in mobile_data.get('claims', []):
            try:
                claim_id = claim_data.pop('id', None) or claim_data.pop('claim_id', None)

                if claim_id:
                    claim = Claim.objects.get(pk=claim_id)
                    serializer = ClaimSerializer(claim, data=claim_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        results['claims']['updated'] += 1
                    else:
                        results['claims']['errors'].append({
                            'id': claim_id,
                            'errors': serializer.errors
                        })
                else:
                    serializer = ClaimSerializer(data=claim_data)
                    if serializer.is_valid():
                        serializer.save()
                        results['claims']['created'] += 1
                    else:
                        results['claims']['errors'].append({
                            'data': claim_data,
                            'errors': serializer.errors
                        })
            except Claim.DoesNotExist:
                results['claims']['errors'].append({
                    'id': claim_id,
                    'error': 'Claim not found'
                })
            except Exception as e:
                results['claims']['errors'].append({
                    'data': claim_data,
                    'error': str(e)
                })

        return results

    def _get_server_updates(self, since_timestamp, user):
        """Get all server-side changes since last sync"""
        # Get user's organization
        org_id = user.organisation_id

        return {
            'farmers': list(
                Farmer.objects.filter(
                    organisation_id=org_id,
                    date_time_added__gt=since_timestamp
                ).values()
            ),
            'farms': list(
                Farm.objects.filter(
                    farmer__organisation_id=org_id,
                    date_time_added__gt=since_timestamp
                ).values()
            ),
            'quotations': list(
                Quotation.objects.filter(
                    farmer__organisation_id=org_id,
                    quotation_date__gt=since_timestamp
                ).values()
            ),
            'claims': list(
                Claim.objects.filter(
                    farmer__organisation_id=org_id,
                    claim_date__gt=since_timestamp
                ).values()
            ),
        }

    def _detect_conflicts(self, mobile_data, server_updates):
        """Detect sync conflicts (same record modified on both sides)"""
        conflicts = []

        # Check farmers
        mobile_ids = {f.get('id') or f.get('farmer_id') for f in mobile_data.get('farmers', []) if
                      f.get('id') or f.get('farmer_id')}
        server_ids = {f['farmer_id'] for f in server_updates['farmers']}
        conflict_ids = mobile_ids & server_ids

        for farmer_id in conflict_ids:
            mobile_version = next(
                (f for f in mobile_data['farmers'] if (f.get('id') or f.get('farmer_id')) == farmer_id),
                None
            )
            server_version = next(
                (f for f in server_updates['farmers'] if f['farmer_id'] == farmer_id),
                None
            )

            if mobile_version and server_version:
                conflicts.append({
                    'type': 'farmer',
                    'id': farmer_id,
                    'mobile_version': mobile_version,
                    'server_version': server_version,
                    'resolution': 'server_wins'  # Default strategy
                })

        return conflicts
