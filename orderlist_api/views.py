from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Prefetch
from syncdata.models import Order, OrderItem  # ← import existing models
from .serializers import OrderSerializer

# If you’re using your existing token permission:
try:
    from syncdata.permissions import TokenOnlyPermission
    _PERMS = [TokenOnlyPermission]
except Exception:
    _PERMS = []  # falls back to open if that permission isn't present

class OrderListView(APIView):
    permission_classes = _PERMS

    def get(self, request):
        """
        Returns only pending orders with customer and item details.
        Optional filters:
          - client_id
          - user_id
          - from_date (YYYY-MM-DD)
          - to_date   (YYYY-MM-DD)
          - order_id  (exact id)
        """
        # Show only pending orders by default
        qs = Order.objects.filter(status="pending").prefetch_related(
            Prefetch("items", queryset=OrderItem.objects.all().order_by("id"))
        ).order_by("-created_at")

        # Filters (optional)
        client_id = request.GET.get("client_id")
        user_id = request.GET.get("user_id")
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        order_id = request.GET.get("order_id")

        if client_id:
            qs = qs.filter(client_id=client_id)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)
        if order_id:
            qs = qs.filter(id=order_id)

        data = OrderSerializer(qs, many=True).data
        return Response({"success": True, "count": len(data), "orders": data}, status=status.HTTP_200_OK)







# http://127.0.0.1:8000/api/orderlist/orders/