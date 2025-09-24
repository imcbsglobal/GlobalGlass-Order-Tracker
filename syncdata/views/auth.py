from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from django.shortcuts import render
from syncdata.models import AccUsers


class LoginView(APIView):
    """
    Login view that authenticates users from acc_users and returns a JWT token,
    user_id and client_id
    """

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        user_id = request.data.get("user_id")
        password = request.data.get("password")
        client_id = request.data.get("client_id")

        if not all([user_id, password, client_id]):
            return Response({
                "success": False,
                "message": "user_id, password, and client_id are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = AccUsers.objects.get(id=user_id, pass_field=password, client_id=client_id)
        except AccUsers.DoesNotExist:
            return Response({
                "success": False,
                "message": "Invalid credentials."
            }, status=status.HTTP_401_UNAUTHORIZED)
        

        # ✅ Create token manually and add required claims
        token = AccessToken()
        token["user_id"] = str(user.id)
        token["client_id"] = user.client_id

        return Response({
            "success": True,
            "token": str(token),
            "user_id": user.id,
            "client_id": user.client_id
        }, status=status.HTTP_200_OK)
