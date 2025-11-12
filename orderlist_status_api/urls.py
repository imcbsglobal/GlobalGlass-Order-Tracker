from django.urls import path
from .views import OrderStatusUpdateView

urlpatterns = [
    path("update/", OrderStatusUpdateView.as_view(), name="order_status_update"),
]
