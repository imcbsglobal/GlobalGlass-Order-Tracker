# GlobalGlass Order Tracker - Database Version

This application has been updated to use a database for order and cart management instead of local storage.

## Key Changes Made

### 1. Database Models
- **Order**: Stores order information with customer details, total amount, and status
- **OrderItem**: Stores individual items within each order
- **Cart**: Stores cart information for each customer
- **CartItem**: Stores individual items within each cart

### 2. API Endpoints
The following API endpoints have been implemented for database operations:

#### Cart Management
- `POST /api/cart/add/` - Add product to cart
- `GET /api/cart/get/` - Get cart items for a customer
- `POST /api/cart/update/` - Update cart item quantity
- `POST /api/cart/remove/` - Remove item from cart
- `POST /api/cart/clear/` - Clear entire cart

#### Order Management
- `POST /api/orders/place/` - Place order from cart
- `GET /api/orders/get/` - Get orders with filtering and pagination
- `POST /api/orders/update-status/` - Update order status
- `POST /api/orders/delete/` - Delete order
- `POST /api/orders/update-item/` - Update order item quantity
- `POST /api/orders/delete-item/` - Delete order item

### 3. Template Updates
All templates have been updated to use database operations:

- **index.html**: Shows orders from database with filtering and search
- **cart.html**: Manages cart using database operations
- **order.html**: Adds products to database cart
- **neworder.html**: Creates orders with database storage

### 4. Features
- **Order History**: View all orders with filtering by date range and status
- **Cart Management**: Persistent cart storage per customer
- **Order Status**: Track order status (pending, completed, cancelled)
- **Real-time Updates**: Live updates when modifying orders or cart
- **Search & Filter**: Search orders by ID or customer name, filter by date range

### 5. Database Schema

#### Orders Table
- `id`: Primary key
- `order_number`: Unique order identifier
- `customer_name`: Customer name
- `customer_phone`: Customer phone number
- `customer_address`: Customer address
- `total_amount`: Order total
- `status`: Order status (pending/completed/cancelled)
- `created_at`: Order creation timestamp
- `updated_at`: Last update timestamp
- `user_id`: User who created the order
- `client_id`: Client identifier

#### Order Items Table
- `id`: Primary key
- `order`: Foreign key to Order
- `product_code`: Product code
- `product_name`: Product name
- `quantity`: Item quantity
- `unit_price`: Unit price
- `total_price`: Total price for this item

#### Cart Table
- `id`: Primary key
- `customer_name`: Customer name
- `customer_phone`: Customer phone
- `customer_address`: Customer address
- `created_at`: Cart creation timestamp
- `updated_at`: Last update timestamp
- `user_id`: User who owns the cart
- `client_id`: Client identifier

#### Cart Items Table
- `id`: Primary key
- `cart`: Foreign key to Cart
- `product_code`: Product code
- `product_name`: Product name
- `quantity`: Item quantity
- `unit_price`: Unit price

## Usage

1. **Create Order**: Go to `/neworder/` to select customer and add products
2. **View Cart**: Go to `/cart/` to see cart items and place order
3. **Order History**: Go to `/index/` to view all orders with filtering options
4. **Manage Orders**: Use the order details modal to update quantities or delete items

## Setup

1. Run migrations: `python manage.py migrate`
2. Create superuser: `python manage.py createsuperuser`
3. Start server: `python manage.py runserver`

## Admin Interface

Access `/admin/` to manage:
- Orders and order items
- Carts and cart items
- View order history and status

The admin interface provides full CRUD operations for all order and cart data.
