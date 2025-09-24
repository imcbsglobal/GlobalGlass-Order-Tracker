from django.urls import path
from .views import OrderListView

urlpatterns = [
    path("api/orderlist/orders/", OrderListView.as_view(), name="orderlist_all_orders"),
]
