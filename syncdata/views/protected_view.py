# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from syncdata.permissions import TokenOnlyPermission


class ProtectedView(APIView):
    permission_classes = [TokenOnlyPermission]

    def get(self, request):
        token = request.auth 
        user_id = token.get("user_id")
        client_id = token.get("client_id")

        return Response({
            "message": "Access granted!",
            "user_id": user_id,
            "client_id": client_id
        })
