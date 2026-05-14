from rest_framework.views import APIView
from rest_framework.response import Response
from syncdata.models import ClientLicense
from syncdata.permissions import TokenOnlyPermission

class LicenseStatusView(APIView):
    permission_classes = [TokenOnlyPermission]

    def get(self, request):
        client_id = request.query_params.get("client_id")
        if not client_id:
            return Response({"success": False, "message": "client_id is required"}, status=400)
        try:
            lic = ClientLicense.objects.get(client_id=client_id)
            return Response({
                "success": True,
                "client_id": lic.client_id,
                "is_active": lic.is_active,
                "expires_at": lic.expires_at,
                "is_valid": lic.is_valid(),
            })
        except ClientLicense.DoesNotExist:
            return Response({"success": False, "message": "No license found"}, status=404)
        