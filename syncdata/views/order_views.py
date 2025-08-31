from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
import json
import uuid
from datetime import datetime, time

from syncdata.models import Order, OrderItem, Cart, CartItem, AccProduct, AccProductBatch, ManualCustomer

@csrf_exempt
@require_http_methods(["POST"])
def add_to_cart(request):
    """Add product to cart"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        client_id = data.get('client_id')
        customer_name = data.get('customer_name', 'Guest')
        customer_phone = data.get('customer_phone', '')
        customer_address = data.get('customer_address', '')
        product_code = data.get('product_code')
        quantity = int(data.get('quantity', 1))
        

        
        # Get product details
        try:
            product = AccProduct.objects.get(code=product_code, client_id=client_id)
        except AccProduct.DoesNotExist:
            # Try to find the product without client_id filter first
            try:
                product = AccProduct.objects.get(code=product_code)
                # If found, check if it has a different client_id
                if product.client_id != client_id:
                    return JsonResponse({
                        'error': f'Product found but belongs to client {product.client_id}, not {client_id}'
                    }, status=404)
            except AccProduct.DoesNotExist:
                return JsonResponse({
                    'error': f'Product with code "{product_code}" not found in database'
                }, status=404)
        
        try:
            # Use filter().order_by().first() to get the batch with highest sales price
            product_batch = AccProductBatch.objects.filter(
                productcode=product_code, 
                client_id=client_id
            ).order_by('-salesprice').first()
            
            if not product_batch:
                # Try to find the batch without client_id filter first
                product_batch = AccProductBatch.objects.filter(
                    productcode=product_code
                ).order_by('-salesprice').first()
                
                if product_batch and product_batch.client_id != client_id:
                    return JsonResponse({
                        'error': f'Product batch found but belongs to client {product_batch.client_id}, not {client_id}'
                    }, status=404)
                elif not product_batch:
                    return JsonResponse({
                        'error': f'Product batch with code "{product_code}" not found in database'
                    }, status=404)
        except Exception as e:
            return JsonResponse({
                'error': f'Error finding product batch: {str(e)}'
            }, status=500)
        
        unit_price = float(product_batch.salesprice or 0)
        
        # Get or create cart for this customer
        cart, created = Cart.objects.get_or_create(
            customer_name=customer_name,
            user_id=user_id,
            client_id=client_id,
            defaults={
                'customer_phone': customer_phone,
                'customer_address': customer_address
            }
        )
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_code=product_code,
            defaults={
                'product_name': product.name or '',
                'quantity': quantity,
                'unit_price': unit_price
            }
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'cart_id': cart.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_cart(request):
    """Get cart items for a customer"""
    try:
        user_id = request.GET.get('user_id')
        client_id = request.GET.get('client_id')
        customer_name = request.GET.get('customer_name', 'Guest')
        
        try:
            cart = Cart.objects.get(
                customer_name=customer_name,
                user_id=user_id,
                client_id=client_id
            )
            
            cart_items = []
            for item in cart.items.all():
                cart_items.append({
                    'id': item.id,
                    'product_code': item.product_code,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.unit_price * item.quantity)
                })
            
            return JsonResponse({
                'success': True,
                'cart': {
                    'id': cart.id,
                    'customer_name': cart.customer_name,
                    'customer_phone': cart.customer_phone,
                    'customer_address': cart.customer_address,
                    'items': cart_items,
                    'total_amount': sum(item['total_price'] for item in cart_items)
                }
            })
            
        except Cart.DoesNotExist:
            return JsonResponse({
                'success': True,
                'cart': {
                    'id': None,
                    'customer_name': customer_name,
                    'customer_phone': '',
                    'customer_address': '',
                    'items': [],
                    'total_amount': 0
                }
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_cart_item(request):
    """Update cart item quantity"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        if quantity <= 0:
            # Remove item if quantity is 0 or negative
            return remove_cart_item(request)
        
        cart_item = CartItem.objects.get(id=item_id)
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart item updated'
        })
        
    except CartItem.DoesNotExist:
        return JsonResponse({'error': 'Cart item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def remove_cart_item(request):
    """Remove item from cart"""
    try:
        data = json.loads(request.body)

        item_id = data.get('product_code')
        client_id = data.get('client_id')
        user_id = data.get('user_id')
        customer_name = data.get('customer_name')

        cart = Cart.objects.get(
            customer_name=customer_name,
            user_id=user_id,
            client_id=client_id
        )

        print(cart)
            
        for item in cart.items.all():
            if (item.product_code == item_id):
                item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart'
        })
        
    except CartItem.DoesNotExist:
        return JsonResponse({'error': 'Cart item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def clear_cart(request):
    """Clear entire cart"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        client_id = data.get('client_id')
        customer_name = data.get('customer_name', 'Guest')
        
        try:
            cart = Cart.objects.get(
                customer_name=customer_name,
                user_id=user_id,
                client_id=client_id
            )
            cart.items.all().delete()
            cart.delete()
        except Cart.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': 'Cart cleared'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def place_order(request):
    """Place order from cart"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        client_id = data.get('client_id')
        customer_name = data.get('customer_name', 'Guest')
        customer_phone = data.get('customer_phone', '')
        customer_address = data.get('customer_address', '')

        with transaction.atomic():
            # Get cart
            try:
                cart = Cart.objects.get(
                    customer_name=customer_name,
                    user_id=user_id,
                    client_id=client_id
                )
            except Cart.DoesNotExist:
                return JsonResponse({'error': 'Cart not found'}, status=404)

            # Check for existing pending order for this user
            order = Order.objects.filter(
                user_id=user_id,
                client_id=client_id,
                customer_name=customer_name,
                status='pending'
            ).first()

            if not order:
                # Create new order if none exists
                order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
                total_amount = sum(item.unit_price * item.quantity for item in cart.items.all())
                order = Order.objects.create(
                    order_number=order_number,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    customer_address=customer_address,
                    total_amount=total_amount,
                    status='pending',
                    user_id=user_id,
                    client_id=client_id
                )

            # Add/merge cart items into order
            for cart_item in cart.items.all():
                order_item = OrderItem.objects.filter(order=order, product_code=cart_item.product_code).first()
                if order_item:
                    # Update existing item
                    order_item.quantity += cart_item.quantity
                    order_item.total_price += cart_item.unit_price * cart_item.quantity
                    order_item.save()
                else:
                    # Create new item
                    OrderItem.objects.create(
                        order=order,
                        product_code=cart_item.product_code,
                        product_name=cart_item.product_name,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.unit_price,
                        total_price=cart_item.unit_price * cart_item.quantity
                    )

            # Update order total amount
            order.total_amount = sum(item.total_price for item in order.items.all())
            order.save()

            # Clear cart
            cart.delete()

            return JsonResponse({
                'success': True,
                'message': 'Order placed successfully',
                'order_id': order.id,
                'order_number': order.order_number
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_orders(request):
    """Get orders with filtering and pagination"""
    try:
        user_id = request.GET.get('user_id')
        client_id = request.GET.get('client_id')
        status = request.GET.get('status', '')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Build query
        orders = Order.objects.filter(user_id=user_id, client_id=client_id)
        
        if status:
            orders = orders.filter(status=status)
            
        orders = orders.order_by('-created_at')
        
        # Paginate
        paginator = Paginator(orders, per_page)
        page_obj = paginator.get_page(page)
        
        # Prepare response data
        orders_data = []
        for order in page_obj:
            order_items = []
            for item in order.items.all():
                order_items.append({
                    'id': item.id,
                    'product_code': item.product_code,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price)
                })
            
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'customer_address': order.customer_address,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'items': order_items,
                'item_count': len(order_items),
                'total_quantity': sum(item.quantity for item in order.items.all())
            })
        
        return JsonResponse({
            'success': True,
            'orders': orders_data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'total_count': page_obj.paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_order_status(request):
    """Update order status"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        order = Order.objects.get(id=order_id)
        order.status = new_status
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Order status updated'
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_order(request):
    """Delete order"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        order = Order.objects.get(id=order_id)
        order.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Order deleted'
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_order_item(request):
    """Update order item quantity"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        if quantity <= 0:
            return delete_order_item(request)
        
        order_item = OrderItem.objects.get(id=item_id)
        order_item.quantity = quantity
        order_item.total_price = order_item.unit_price * quantity
        order_item.save()
        
        # Update order total
        order = order_item.order
        order.total_amount = sum(item.total_price for item in order.items.all())
        order.save()
        
        return JsonResponse({
            'success': True,
            'totalAmount': order.total_amount,
            'message': 'Order item updated'
        })
        
    except OrderItem.DoesNotExist:
        return JsonResponse({'error': 'Order item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_order_item(request):
    """Delete order item"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        order_item = OrderItem.objects.get(id=item_id)
        order = order_item.order
        order_item.delete()
        
        # Update order total
        order.total_amount = sum(item.total_price for item in order.items.all())
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Order item deleted'
        })
        
    except OrderItem.DoesNotExist:
        return JsonResponse({'error': 'Order item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

