#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

print("=== Checking Database Tables ===")

with connection.cursor() as cursor:
    # Get all table names
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name;
    """)
    
    tables = cursor.fetchall()
    print(f"Found {len(tables)} tables:")
    
    for table in tables:
        table_name = table[0]
        print(f"  - {table_name}")
        
        # Check if it's one of our expected tables
        if table_name in ['carts', 'cart_items', 'orders', 'order_items']:
            print(f"    ✓ Found expected table: {table_name}")
        elif table_name.startswith('django_') or table_name.startswith('auth_'):
            print(f"    (Django system table: {table_name})")
        else:
            print(f"    (Other table: {table_name})")

print("\n=== Checking Migration Status ===")
from django.db.migrations.executor import MigrationExecutor
from django.db import connection

executor = MigrationExecutor(connection)
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
if plan:
    print("Pending migrations:")
    for migration, backwards in plan:
        print(f"  - {migration}")
else:
    print("No pending migrations")

print("\n=== Checking if Cart table exists ===")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM carts")
        count = cursor.fetchone()[0]
        print(f"Cart table exists with {count} records")
except Exception as e:
    print(f"Cart table does not exist: {e}")

print("\n=== Checking if CartItem table exists ===")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM cart_items")
        count = cursor.fetchone()[0]
        print(f"CartItem table exists with {count} records")
except Exception as e:
    print(f"CartItem table does not exist: {e}")

