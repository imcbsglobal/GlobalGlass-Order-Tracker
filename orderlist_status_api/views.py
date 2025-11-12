from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from syncdata.models import Order  # Use the existing Order model
from syncdata.permissions import TokenOnlyPermission

class OrderStatusUpdateView(APIView):
    permission_classes = [TokenOnlyPermission]

    def post(self, request):
        """
        API to update order status.
        Required fields:
          - order_id
          - status (pending | completed | cancelled)
        """
        order_id = request.data.get("order_id")
        new_status = request.data.get("status")

        # Validate input
        if not order_id or not new_status:
            return Response(
                {"success": False, "message": "order_id and status are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status not in ["pending", "completed", "cancelled"]:
            return Response(
                {"success": False, "message": "Invalid status. Choose pending, completed, or cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(id=order_id)
            order.status = new_status
            order.save()

            return Response(
                {"success": True, "message": f"Order status updated to {new_status}."},
                status=status.HTTP_200_OK
            )

        except Order.DoesNotExist:
            return Response(
                {"success": False, "message": "Order not found."},
                status=status.HTTP_404_NOT_FOUND
            )
