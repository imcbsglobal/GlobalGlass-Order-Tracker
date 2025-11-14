from rest_framework import serializers
from syncdata.models import Order, OrderItem, AccProductBatch

class OrderItemSerializer(serializers.ModelSerializer):
    barcode = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_code",
            "product_name",
            "quantity",
            "unit_price",
            "discount_pct",
            "total_price",
            "barcode",
            "discount",
        ]

    # 📌 Fetch barcode from batch table
    def get_barcode(self, obj):
        batch = AccProductBatch.objects.filter(productcode=obj.product_code).first()
        return batch.barcode if batch else None

    # 📌 Fetch discounted price from batch table
    def get_discount(self, obj):
        batch = AccProductBatch.objects.filter(productcode=obj.product_code).first()
        return batch.discounted_price if batch else None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer_name",
            "customer_phone",
            "customer_address",
            "total_amount",
            "status",
            "created_at",
            "items",
        ]
