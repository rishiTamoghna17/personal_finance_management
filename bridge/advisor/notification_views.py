from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PushDevice


class PushDeviceView(APIView):
    """Register or remove this authenticated phone's FCM token."""

    def post(self, request):
        token = request.data.get("token") if isinstance(request.data, dict) else None
        if not isinstance(token, str) or not 20 <= len(token) <= 4096 or any(ch.isspace() for ch in token):
            return Response({"detail": "A valid FCM registration token is required."}, status=400)
        digest = PushDevice.hash_token(token)
        device, _ = PushDevice.objects.update_or_create(
            token_hash=digest,
            defaults={"token": token, "active": True},
        )
        return Response({"registered": True})

    def delete(self, request):
        token = request.data.get("token") if isinstance(request.data, dict) else None
        if not isinstance(token, str) or not token:
            return Response({"detail": "A valid FCM registration token is required."}, status=400)
        PushDevice.objects.filter(token_hash=PushDevice.hash_token(token)).delete()
        return Response({"registered": False})
