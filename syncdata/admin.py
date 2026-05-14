from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem, ClientLicense

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'quantity', 'unit_price', 'total_price']
    list_filter = ['order__status']
    search_fields = ['product_name', 'product_code']
    readonly_fields = ['total_price']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'user_id', 'client_id', 'created_at']
    list_filter = ['created_at']
    search_fields = ['customer_name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product_name', 'quantity', 'unit_price']
    list_filter = ['cart__created_at']
    search_fields = ['product_name', 'product_code']

@admin.register(ClientLicense)
class ClientLicenseAdmin(admin.ModelAdmin):
    list_display = ['client_id', 'license_key', 'is_active', 'expires_at', 'created_at']
    list_filter = ['is_active']
    search_fields = ['client_id', 'license_key']
    readonly_fields = ['created_at', 'updated_at']