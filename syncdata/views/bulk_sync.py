from django.db import transaction
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
import logging

from syncdata.models import AccProduct, AccMaster, AccProductBatch, AccUsers
from syncdata.serializers import (
    AccMasterSerializer, AccProductBatchSerializer, AccUsersSerializer, AccProductSerializer
)

logger = logging.getLogger(__name__)


def index_view(request):
    context = {
        'user': {
            'id': request.user.id if request.user.is_authenticated else None,
            'username': request.user.id if request.user.is_authenticated else 'Guest',
            'client_id': getattr(request.user, 'client_id', 'CLIENT_001')
        }
    }
    return render(request, 'index.html', context)

def login_view(request):
    return render(request, 'login.html')

def order_view(request):
    context = {
        'user': {
            'id': request.user.id if request.user.is_authenticated else None,
            'username': request.user.id if request.user.is_authenticated else 'Guest',
            'client_id': getattr(request.user, 'client_id', 'CLIENT_001')
        }
    }
    return render(request, 'order.html', context)

def cart_view(request):
    context = {
        'user': {
            'id': request.user.id if request.user.is_authenticated else None,
            'username': request.user.username if request.user.is_authenticated else 'Guest',
            'client_id': getattr(request.user, 'client_id', 'CLIENT_001')
        }
    }
    return render(request, 'cart.html', context)






class BulkSyncDataView(APIView):
    """Bulk sync endpoint that deletes data based on client_id before inserting"""

                      
    def get_model_and_serializer(self, table_name):
        table_mapping = {
            'users': (AccUsers, AccUsersSerializer),
            'products': (AccProduct, AccProductSerializer),
            'batches': (AccProductBatch,AccProductBatchSerializer),
            'customers': (AccMaster, AccMasterSerializer),
        }
        return table_mapping.get(table_name, (None, None))

    def clear_table_for_client(self, model, client_id):
        """Clear data only for the given client_id"""
        try:
            deleted_count = model.objects.filter(client_id=client_id).delete()[0]
            logger.info(f"Deleted {deleted_count} records for client_id {client_id} from {model._meta.db_table}")
            return True
        except Exception as e:
            logger.error(f"Error deleting client_id {client_id} from {model._meta.db_table}: {str(e)}")
            return False

    def bulk_insert_data(self, model, data_list, batch_size=2000):
        try:
            total_inserted = 0
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                instances = []

                for data in batch:
                    if 'class' in data:
                        data['class_field'] = data.pop('class')
                    instances.append(model(**data))

                created_instances = model.objects.bulk_create(
                    instances, batch_size=batch_size, ignore_conflicts=False
                )
                total_inserted += len(created_instances)

            logger.info(f"Inserted {total_inserted} records into {model._meta.db_table}")
            return True, total_inserted
        except Exception as e:
            logger.error(f"Bulk insert error in {model._meta.db_table}: {str(e)}")
            return False, 0

    def post(self, request):
        try:
            data = request.data
            tables_data = data.get('tables', {})
            client_id = data.get('client_id')

            if not client_id:
                return Response({
                    'success': False,
                    'error': 'Missing client_id'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not tables_data:
                return Response({
                    'success': False,
                    'error': 'No table data provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            sync_order = ['products', 'batches', 'customers', 'users']

            results = {}
            total_processed = 0

            with transaction.atomic():
                for table_name in sync_order:
                    if table_name not in tables_data:
                        continue

                    model, serializer_class = self.get_model_and_serializer(table_name)
                    if not model:
                        return Response({
                            'success': False,
                            'error': f"Unknown table: {table_name}"
                        }, status=status.HTTP_400_BAD_REQUEST)

                    table_data = tables_data[table_name]
                    logger.info(f"Processing table {table_name}: {len(table_data)} records")

                    # ✅ Clear only data belonging to this client_id
                    if not self.clear_table_for_client(model, client_id):
                        return Response({
                            'success': False,
                            'error': f"Failed to clear table {table_name} for client_id {client_id}"
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    # Add client_id to all records if not already present
                    for record in table_data:
                        record['client_id'] = client_id

                    # 🔁 Bulk insert
                    if table_data:
                        success, inserted_count = self.bulk_insert_data(model, table_data, batch_size=3000)
                        if not success:
                            return Response({
                                'success': False,
                                'error': f"Failed to insert into table {table_name}"
                            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    else:
                        inserted_count = 0

                    results[table_name] = {
                        'records_processed': inserted_count,
                        'table_cleared_for_client': True
                    }
                    total_processed += inserted_count

            return Response({
                'success': True,
                'message': f'Successfully synced {total_processed} records for client {client_id}',
                'client_id': client_id,
                'results': results,
                'total_processed': total_processed
            })

        except Exception as e:
            logger.exception(f"Bulk sync failed: {str(e)}")
            return Response({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
