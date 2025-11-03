from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from collections import defaultdict
from syncdata.permissions import TokenOnlyPermission
from django.db import models
from syncdata.models import AccMaster, ManualCustomer, AccProductBatch, AccProduct


class CustomerView(APIView):
    permission_classes = [TokenOnlyPermission]

    def get(self, request):
        client_id = request.auth.get("client_id") if request.auth else None

        if not client_id:
            return Response({"error": "Client ID not found in token"}, status=400)

        synced = AccMaster.objects.filter(client_id=client_id).values(
            "code", "name", "phone", "address", "client_id"
        )

        manual = ManualCustomer.objects.filter(client_id=client_id).annotate(
            code=models.F("client_id")
        ).values("code", "name", "phone", "address", "client_id")

        customers = list(synced) + list(manual)
        return Response(customers)

    def post(self, request):
        try:
            if not request.auth:
                return Response({"success": False, "message": "Authentication failed"}, status=401)

            client_id = request.auth.get("client_id")
            if not client_id:
                return Response({"success": False, "message": "Missing client ID"}, status=400)

            data = request.data
            name = data.get("name")
            address = data.get("address", "")
            phone = data.get("phone", "")

            if not name:
                return Response({"success": False, "message": "Name is required."}, status=400)

            if ManualCustomer.objects.filter(client_id=client_id, name=name).exists():
                return Response({"success": False, "message": "Customer already exists."}, status=409)

            ManualCustomer.objects.create(
                client_id=client_id,
                name=name,
                address=address,
                phone=phone
            )

            return Response({"success": True, "message": "Customer added successfully."}, status=201)

        except Exception as e:
            print("❌ Error in POST /customers/:", str(e))
            return Response({"success": False, "message": "Server error"}, status=500)


class ProductView(APIView):
    permission_classes = [TokenOnlyPermission]

    def get(self, request):
        print("✅ ProductView HIT!")

        client_id = request.auth.get("client_id") if request.auth else None
        if not client_id:
            return Response({"error": "Client ID not found in token"}, status=400)

        products = AccProduct.objects.filter(client_id=client_id).order_by("code")

        # Dynamically set the page size to the total number of products
        paginator = PageNumberPagination()
        paginator.page_size = products.count()  # Set page size to the total number of products
        paginated_products = paginator.paginate_queryset(products, request)

        # Fetch all batches in one go
        batches = AccProductBatch.objects.filter(client_id=client_id)
        batch_map = {batch.productcode: batch for batch in batches}

        final_data = []
        for product in paginated_products:
            batch = batch_map.get(product.code)

            final_data.append({
                "code": product.code,
                "name": product.name,
                "product": product.product,
                "brand": product.brand,
                "unit": product.unit,
                "taxcode": product.taxcode,
                "defect": product.defect,
                "company": product.company,
                "client_id": product.client_id,
                "batch": {
                    # Price values
                    "cost": batch.cost if batch else None,
                    "salesprice": batch.salesprice if batch else None,
                    "bmrp": batch.bmrp if batch else None,
                    "secondprice": batch.secondprice if batch else None,
                    "thirdprice": batch.thirdprice if batch else None,
                    "fourthprice": batch.fourthprice if batch else None,
                    
                    # Price names (newly added)
                    "cost_name": batch.cost_name if batch else None,
                    "sales_price_name": batch.sales_price_name if batch else None,
                    "bmrp_name": batch.bmrp_name if batch else None,
                    "secondprice_name": batch.secondprice_name if batch else None,
                    "thirdprice_name": batch.thirdprice_name if batch else None,
                    "fourthprice_name": batch.fourthprice_name if batch else None,
                    
                    # Other batch info
                    "barcode": batch.barcode if batch else None,
                } if batch else None
            })

        return paginator.get_paginated_response(final_data)