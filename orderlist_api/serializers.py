from rest_framework import serializers
from syncdata.models import Order, OrderItem  # ← import, no new models

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_code",
            "product_name",
            "quantity",
            "unit_price",
            "total_price",
        ]

class OrderSerializer(serializers.ModelSerializer):
    # include nested items
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            # customer details already stored on Order
            "customer_name",
            "customer_phone",
            "customer_address",
            "total_amount",
            "status",
            "created_at",
            "updated_at",
            "user_id",
            "client_id",
            "items",
        ]
