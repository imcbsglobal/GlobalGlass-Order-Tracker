import requests
import logging
from syncdata.models import ClientLicense

ACTIVATION_URL = "https://activate.imcbs.com/mobileapp/api/project/glassx/"

logger = logging.getLogger(__name__)


def fetch_licenses_from_server():
    try:
        response = requests.get(ACTIVATION_URL, timeout=5)
        data = response.json()
        if data.get("success"):
            return data.get("customers", [])
        return []
    except Exception as e:
        logger.error("Failed to fetch licenses from server: %s", e)
        return []


def validate_client_license(client_id):
    try:
        lic = ClientLicense.objects.get(client_id=client_id)
        if lic.is_valid():
            return True, "License valid"
        return False, "License expired or inactive"
    except ClientLicense.DoesNotExist:
        return False, "No license found for this client"


def sync_licenses_from_server():
    from django.utils.dateparse import parse_date
    from django.utils.timezone import make_aware
    from datetime import datetime, time

    customers = fetch_licenses_from_server()

    if not customers:
        logger.warning("No customers returned from activation server.")
        return

    valid_client_ids = []  # ✅ track valid clients from API

    for customer in customers:
        client_id = customer.get("client_id")
        license_key = customer.get("license_key")

        validity = customer.get("license_validity", {})
        expiry_date = validity.get("expiry_date")
        is_expired = validity.get("is_expired", True)

        status = customer.get("status", "")
        is_active = (status.strip().lower() == "active") and not is_expired

        if not client_id or not license_key or not expiry_date:
            logger.warning("Skipping customer entry with missing fields: %s", customer)
            continue

        parsed_date = parse_date(expiry_date)
        if not parsed_date:
            logger.warning("Could not parse expiry_date '%s' for client_id=%s", expiry_date, client_id)
            continue

        parsed_expiry = make_aware(datetime.combine(parsed_date, time.max))

        ClientLicense.objects.update_or_create(
            client_id=client_id,
            defaults={
                "license_key": license_key,
                "is_active": is_active,
                "expires_at": parsed_expiry,
            }
        )

        valid_client_ids.append(client_id)  # ✅ add to valid list
        logger.info("License synced for client_id=%s | active=%s | expires=%s", client_id, is_active, parsed_expiry)

    # ✅ THIS IS THE KEY LINE - deletes anyone not in the API response
    deleted, _ = ClientLicense.objects.exclude(client_id__in=valid_client_ids).delete()
    if deleted:
        logger.info("Removed %d stale licenses not in API response.", deleted)