from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from datetime import datetime

from insurance.models import Farmer, Farm, Quotation, Claim
from insurance.serializers import (
    FarmerSerializer,
    FarmSerializer,
    QuotationSerializer,
    ClaimSerializer,
)

ENTITY_MAP = {
    "farmers": (Farmer, FarmerSerializer),
    "farms": (Farm, FarmSerializer),
    "quotations": (Quotation, QuotationSerializer),
    "claims": (Claim, ClaimSerializer),
}


class SyncAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        payload = request.data

        last_sync = payload.get("last_sync_timestamp")
        pending_data = payload.get("pending_data", {})

        last_sync_dt = self._parse_timestamp(last_sync)

        with transaction.atomic():
            upload_results = self._process_uploads(pending_data, user)
            server_updates = self._get_server_updates(last_sync_dt, user)
            conflicts = []  # server-wins strategy for now

        return Response({
            "upload_results": upload_results,
            "server_updates": server_updates,
            "conflicts": conflicts,
            "sync_timestamp": timezone.now().isoformat(),
            "status": "success",
        })

    # ================= HELPERS =================

    def _parse_timestamp(self, ts):
        if not ts:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    @transaction.atomic
    def _process_uploads(self, pending_data, user):
        results = {}

        for entity, items in pending_data.items():
            model, serializer_class = ENTITY_MAP[entity]
            created = updated = 0
            errors = []

            for item in items:
                local_id = item.pop("id", None)

                try:
                    if local_id:
                        obj = model.objects.filter(
                            id=local_id,
                            organisation=user.organisation
                        ).first()

                        if obj:
                            serializer = serializer_class(
                                obj, data=item, partial=True
                            )
                            serializer.is_valid(raise_exception=True)
                            serializer.save()
                            updated += 1
                        else:
                            errors.append({
                                "id": local_id,
                                "error": "Record not found on server"
                            })
                    else:
                        serializer = serializer_class(data=item)
                        serializer.is_valid(raise_exception=True)
                        serializer.save(organisation=user.organisation)
                        created += 1

                except Exception as e:
                    errors.append({
                        "data": item,
                        "error": str(e)
                    })

            results[entity] = {
                "created": created,
                "updated": updated,
                "errors": errors,
            }

        return results

    def _get_server_updates(self, since, user):
        org = user.organisation

        return {
            "farmers": FarmerSerializer(
                Farmer.objects.filter(
                    organisation=org,
                    updated_at__gt=since
                ),
                many=True
            ).data,

            "farms": FarmSerializer(
                Farm.objects.filter(
                    farmer__organisation=org,
                    updated_at__gt=since
                ),
                many=True
            ).data,

            "quotations": QuotationSerializer(
                Quotation.objects.filter(
                    farmer__organisation=org,
                    updated_at__gt=since
                ),
                many=True
            ).data,

            "claims": ClaimSerializer(
                Claim.objects.filter(
                    farmer__organisation=org,
                    updated_at__gt=since
                ),
                many=True
            ).data,
        }
