from django.urls import path

# Auth & Core Views
from syncdata.views.auth import LoginView
from syncdata.views.protected_view import ProtectedView
from syncdata.views.bulk_sync import BulkSyncDataView, cart_view, order_view, index_view

# Order Management Views
from syncdata.views.order_views import (
    add_to_cart, get_cart, update_cart_item, remove_cart_item,
    place_order, get_orders, update_order_status, delete_order, clear_cart,
    update_order_item, delete_order_item
)

from syncdata.views.app_view import CustomerView, ProductView

urlpatterns = [
    # Auth
    path('', LoginView.as_view(), name='login'),
    path('protected/', ProtectedView.as_view(), name='protected'),

    # Sync routes
    path('sync/bulk/', BulkSyncDataView.as_view(), name='bulk-sync'),

    # UI PAGES GETTING ROUTES
    path('login/', LoginView.as_view(), name='login-page'),
    path('orders/', order_view, name='orders'),
    path('cart/', cart_view, name='cart'),
    path('index/', index_view, name='index'),

    # 🧾 Customer Routes 
    # (Frontend dropdown & add customer)
    path('customers/', CustomerView.as_view(), name='customers'),

    # 📦 Product Routes
    path('products/', ProductView.as_view(), name='products'),
    
    # 🛒 Cart Management API
    path('api/cart/add/', add_to_cart, name='add_to_cart'),
    path('api/cart/get/', get_cart, name='get_cart'),
    path('api/cart/update/', update_cart_item, name='update_cart_item'),
    path('api/cart/remove/', remove_cart_item, name='remove_cart_item'),
    path('api/cart/clear/', clear_cart, name='clear_cart'),
    
    # 📋 Order Management API
    path('api/orders/place/', place_order, name='place_order'),
    path('api/orders/get/', get_orders, name='get_orders'),
    path('api/orders/update-status/', update_order_status, name='update_order_status'),
    path('api/orders/delete/', delete_order, name='delete_order'),
    
    # 📋 Order Item Management API
    path('api/orders/update-item/', update_order_item, name='update_order_item'),
    path('api/orders/delete-item/', delete_order_item, name='delete_order_item'),
]
