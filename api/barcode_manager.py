import uuid
from datetime import datetime
from django.utils import timezone
from core.models import Client, Order, KitBarcodeAssignment

class BarcodeError(Exception):
    """Base exception for barcode operations."""
    pass

class ClientNotFoundError(BarcodeError):
    """Raised when the specified client does not exist."""
    pass

class BarcodeNotFoundError(BarcodeError):
    """Raised when the specified barcode assignment does not exist."""
    pass

class BarcodeConflictError(BarcodeError):
    """Raised when a barcode is already linked to another client."""
    pass

class BarcodeMismatchError(BarcodeError):
    """Raised when a barcode does not match the active order's test kit assignment."""
    pass

class OrderNotFoundError(BarcodeError):
    """Raised when the specified order does not exist."""
    pass


class BarcodeManager:
    @staticmethod
    def link_barcode_to_client(barcode_number: str, client_id: int) -> tuple[KitBarcodeAssignment, bool]:
        """
        Links a barcode to a client and their active order. Creates an order if none exists.
        Returns a tuple of (KitBarcodeAssignment, already_linked).
        """
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            raise ClientNotFoundError("Client not found")

        try:
            assignment = KitBarcodeAssignment.objects.select_related("client", "test_kit", "order").get(barcode_number=barcode_number)
        except KitBarcodeAssignment.DoesNotExist:
            raise BarcodeNotFoundError("Barcode not found")

        if assignment.client_id and assignment.client_id != client.id:
            raise BarcodeConflictError("Barcode is already linked to another client")

        # Find client's active pending order
        active_order = Order.objects.filter(client=client).exclude(status__in=["FINISHED", "CANCELLED"]).first()
        
        if not active_order:
            active_order = Order.objects.create(
                client=client,
                order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                status="CREATED"
            )
            assignment.order = active_order
            assignment.client = client
            assignment.save(update_fields=["order", "client", "updated_at"])
            already_linked = False
        else:
            assigned_barcode = getattr(active_order, "barcode_assignment", None)
            already_linked = (
                assignment.client_id == client.id and 
                assignment.order_id == active_order.id
            )

            if not assigned_barcode:
                assignment.order = active_order
                assignment.client = client
                assignment.save(update_fields=["order", "client", "updated_at"])
                assigned_barcode = assignment

            if assigned_barcode.barcode_number != barcode_number:
                raise BarcodeMismatchError("This barcode does not match the kit assigned to your order. Please check the barcode or contact support.")

            if not already_linked:
                assignment.client = client
                assignment.order = active_order
                assignment.save(update_fields=["client", "order", "updated_at"])

        return assignment, already_linked

    @staticmethod
    def unlink_barcode_from_client(barcode_number: str, client_id: int) -> bool:
        """
        Clears client and order relations from a barcode assignment, 
        and restores a fresh placeholder KIT- barcode if an active order was associated with it.
        """
        assignment = KitBarcodeAssignment.objects.filter(barcode_number=barcode_number, client_id=client_id).first()
        if not assignment:
            raise BarcodeNotFoundError("Barcode assignment not found")

        order = getattr(assignment, "order", None)
        test_kit = order.test_kit if order else None

        # Clear relations
        assignment.client = None
        assignment.order = None
        assignment.save(update_fields=["client", "order", "updated_at"])

        # If there was an associated active order, restore a fresh placeholder KIT- barcode
        if order:
            placeholder = "KIT-" + uuid.uuid4().hex[:8].upper()
            KitBarcodeAssignment.objects.create(
                client=order.client,
                order=order,
                test_kit=test_kit,
                barcode_number=placeholder
            )

        return True

    @staticmethod
    def mark_collected(
        barcode_number: str, 
        client_id: int | None = None, 
        collected_at: datetime | None = None
    ) -> KitBarcodeAssignment:
        """
        Updates the collected_at timestamp for a linked barcode assignment.
        """
        try:
            assignment = KitBarcodeAssignment.objects.select_related("client", "test_kit", "order").get(barcode_number=barcode_number)
        except KitBarcodeAssignment.DoesNotExist:
            raise BarcodeNotFoundError("Barcode not found")

        if client_id and assignment.client_id and assignment.client_id != int(client_id):
            raise BarcodeConflictError("Barcode is linked to another client")

        if not collected_at:
            collected_at = timezone.now()

        assignment.collected_at = collected_at
        assignment.save(update_fields=["collected_at", "updated_at"])

        return assignment

    @staticmethod
    def assign_barcode_to_order(kit_code: str, barcode_number: str) -> tuple[KitBarcodeAssignment, bool]:
        """
        Attach a barcode to an existing order and its associated client/test kit.
        """
        try:
            order = Order.objects.select_related("client").prefetch_related("barcode_assignments__test_kit").get(order_number=kit_code)
        except Order.DoesNotExist:
            raise OrderNotFoundError("Order not found for kit_code")

        assignment, created = KitBarcodeAssignment.objects.update_or_create(
            barcode_number=barcode_number,
            defaults={
                "client": order.client,
                "order": order,
                "test_kit": order.test_kit,
            },
        )

        return assignment, created