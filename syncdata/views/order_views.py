import json
import uuid
from datetime import datetime, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator

from syncdata.models import Order, OrderItem, Cart, CartItem, AccProduct, AccProductBatch, ManualCustomer


# ---------------- helpers ----------------
def parse_decimal(value, default='0'):
    """Safely parse a numeric input into Decimal."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(str(default))

def dec_to_json(d):
    """Convert Decimal to float for JSON output (2 decimal places for money)."""
    if isinstance(d, Decimal):
        return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return d

@csrf_exempt
@require_http_methods(["POST"])
def add_to_cart(request):
    """Add product to cart (Decimal-safe)"""
    try:
        data = json.loads(request.body)

        user_id = data.get('user_id')
        client_id = data.get('client_id')
        customer_name = data.get('customer_name', 'Guest')
        customer_phone = data.get('customer_phone', '')
        customer_address = data.get('customer_address', '')
        product_code = data.get('product_code')
        quantity = parse_decimal(data.get('quantity', '1'))

        if not user_id or not client_id or not product_code:
            return JsonResponse({'error': 'user_id, client_id and product_code are required'}, status=400)

        # --- Product lookup ---
        try:
            product = AccProduct.objects.get(code=product_code, client_id=client_id)
        except AccProduct.DoesNotExist:
            # try without client filter, but enforce mismatch error if different client
            product = AccProduct.objects.filter(code=product_code).first()
            if not product:
                return JsonResponse({'error': f'Product with code "{product_code}" not found in database'}, status=404)
            if product.client_id != client_id:
                return JsonResponse({'error': f'Product found but belongs to client {product.client_id}, not {client_id}'}, status=404)

        # --- Batch lookup (highest price preferred) ---
        try:
            product_batch = (
                AccProductBatch.objects
                .filter(productcode=product_code, client_id=client_id)
                .order_by('-salesprice')
                .first()
            )
            if not product_batch:
                product_batch = (
                    AccProductBatch.objects
                    .filter(productcode=product_code)
                    .order_by('-salesprice')
                    .first()
                )
                if not product_batch:
                    return JsonResponse({'error': f'Product batch with code "{product_code}" not found in database'}, status=404)
                if product_batch.client_id != client_id:
                    return JsonResponse({'error': f'Product batch found but belongs to client {product_batch.client_id}, not {client_id}'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Error finding product batch: {str(e)}'}, status=500)

        # --- Determine unit price (prefer frontend, else fallback by key order) ---
        price_key = data.get('price_key')
        frontend_unit_price = data.get('unit_price')

        if frontend_unit_price is not None:
            unit_price = parse_decimal(frontend_unit_price, '0')
        else:
            def get_batch_price(batch, key):
                if not batch or not key:
                    return None
                return getattr(batch, key, None)

            preferred_order = (
                [price_key, 'cost','salesprice','bmrp','secondprice','thirdprice','fourthprice']
                if price_key and price_key != 'all'
                else ['cost','salesprice','bmrp','secondprice','thirdprice','fourthprice']
            )


            unit_price_val = None
            for k in preferred_order:
                val = get_batch_price(product_batch, k)
                if val is not None:
                    unit_price_val = val
                    break

            unit_price = parse_decimal(unit_price_val, '0')

        # --- Get or create cart ---
        cart, _ = Cart.objects.get_or_create(
            customer_name=customer_name,
            user_id=user_id,
            client_id=client_id,
            defaults={
                'customer_phone': customer_phone,
                'customer_address': customer_address,
            },
        )

        # --- Add or update cart item ---
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_code=product_code,
            defaults={
                'product_name': product.name or '',
                'quantity': quantity,
                'unit_price': unit_price,  # Decimal
            },
        )

        if not created:
            current_qty = cart_item.quantity or Decimal('0')
            add_qty = quantity or Decimal('0')
            new_quantity = current_qty + add_qty

            if new_quantity <= 0:
                cart_item.delete()
                return JsonResponse({'success': True, 'message': 'Product removed from cart'})
            else:
                cart_item.quantity = new_quantity
                cart_item.unit_price = unit_price  # keep latest chosen price
                cart_item.save()
        else:
            # ensure latest price is stored even if created with defaults
            cart_item.unit_price = unit_price
            cart_item.save()

        # --- Compute line total (Decimal) ---
        line_total = (cart_item.unit_price or Decimal('0')) * (cart_item.quantity or Decimal('0'))

        # --- Response ---
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'cart_id': cart.id,
            'cart_item': {
                'id': cart_item.id,
                'product_code': cart_item.product_code,
                'product_name': cart_item.product_name,
                'quantity': str(cart_item.quantity),              # preserve 3dp
                'unit_price': dec_to_json(cart_item.unit_price),  # -> float with 2dp
                'line_total': dec_to_json(line_total),            # -> float with 2dp
            },
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
                    'quantity': str(item.quantity),
                    'unit_price': dec_to_json(item.unit_price),
                    'total_price': dec_to_json((item.unit_price or Decimal('0')) * (item.quantity or Decimal('0')))
                })

            total_amount = sum(
                (item['total_price'] if isinstance(item['total_price'], (int, float)) else float(item['total_price']))
                for item in cart_items
            ) if cart_items else 0.0

            return JsonResponse({
                'success': True,
                'cart': {
                    'id': cart.id,
                    'customer_name': cart.customer_name,
                    'customer_phone': cart.customer_phone,
                    'customer_address': cart.customer_address,
                    'items': cart_items,
                    'total_amount': total_amount
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
        quantity = parse_decimal(data.get('quantity', '1'))

        
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
    """Place order from cart (preserves discount)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        client_id = data.get('client_id')
        customer_name = data.get('customer_name', 'Guest')
        customer_phone = data.get('customer_phone', '')
        customer_address = data.get('customer_address', '')

        # optional discount fields coming from cart.html
        subtotal_client = Decimal(str(data.get('subtotal') or '0'))
        discount_client = Decimal(str(data.get('discount') or '0'))
        final_total_client = Decimal(str(data.get('final_total') or '0'))
        items_client = data.get('items') or []  # [{product_code, quantity, unit_price, total_price}, ...]

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

            # Build server-side subtotal from cart
            server_subtotal = Decimal('0.00')
            lines = []
            for ci in cart.items.all():
                qty = ci.quantity or Decimal('0')
                price = ci.unit_price or Decimal('0')
                line = {
                    'code': ci.product_code,
                    'name': ci.product_name,
                    'qty': qty,
                    'unit': price,
                    'orig_total': (price * qty),
                }
                server_subtotal += line['orig_total']
                lines.append(line)

            # Determine discount ratio.
            # Prefer the client-provided discount if subtotal matches; else fall back to 0.
            ratio = Decimal('0')
            if subtotal_client > 0 and abs(subtotal_client - server_subtotal) <= Decimal('0.01'):
                # accept client discount
                ratio = (discount_client / subtotal_client) if subtotal_client != 0 else Decimal('0')
            # clamp
            if ratio < 0:
                ratio = Decimal('0')
            if ratio > 1:
                ratio = Decimal('1')

            # Find or create pending order
            order = Order.objects.filter(
                user_id=user_id, client_id=client_id,
                customer_name=customer_name, status='pending'
            ).first()

            if not order:
                order_number = f"ORD-{timezone.localdate().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
                order = Order.objects.create(
                    order_number=order_number,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    customer_address=customer_address,
                    total_amount=Decimal('0.00'),
                    status='pending',
                    user_id=user_id,
                    client_id=client_id
                )

            # Merge cart → order with discounted totals
            for ln in lines:
                discounted_line = (ln['orig_total'] * (Decimal('1') - ratio)).quantize(Decimal('0.01'))
                oi = OrderItem.objects.filter(order=order, product_code=ln['code']).first()
                if oi:
                    oi.quantity = (oi.quantity or Decimal('0')) + ln['qty']
                    oi.total_price = (oi.total_price or Decimal('0.00')) + discounted_line
                    oi.unit_price = ln['unit']  # keep latest unit
                    oi.save()
                else:
                    OrderItem.objects.create(
                        order=order,
                        product_code=ln['code'],
                        product_name=ln['name'],
                        quantity=ln['qty'],
                        unit_price=ln['unit'],
                        total_price=discounted_line,
                    )

            # Recompute order total as sum of discounted line totals
            order.total_amount = sum(i.total_price for i in order.items.all())
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
        from_date = request.GET.get('from_date')  # YYYY-MM-DD
        to_date = request.GET.get('to_date')      # YYYY-MM-DD
        order_id = request.GET.get('order_id')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Build query
        orders = Order.objects.filter(user_id=user_id, client_id=client_id)

        if order_id:
            orders = orders.filter(id=order_id)
        
        if status:
            orders = orders.filter(status=status)

        if from_date:
            orders = orders.filter(updated_at__date__gte=from_date)
        if to_date:
            orders = orders.filter(updated_at__date__lte=to_date)
        orders = orders.order_by('-updated_at')
        
        # Paginate unless requesting a specific order_id
        if order_id:
            page_obj = list(orders)
        else:
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
                'created_at': timezone.localtime(order.created_at).isoformat(),
                'updated_at': timezone.localtime(order.updated_at).isoformat(),
                'items': order_items,
                'item_count': len(order_items),
                'total_quantity': sum(item.quantity for item in order.items.all())
            })
        
        if order_id:
            # When fetching a specific order, skip pagination metadata
            return JsonResponse({
                'success': True,
                'orders': orders_data,
            })
        else:
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
        quantity = parse_decimal(data.get('quantity', '1'))

        
        if quantity <= 0:
            return delete_order_item(request)
        
        order_item = OrderItem.objects.get(id=item_id)
        order_item.quantity = quantity
        order_item.total_price = (order_item.unit_price or Decimal('0')) * (quantity or Decimal('0'))

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
