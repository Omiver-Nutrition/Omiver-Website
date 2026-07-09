from core.models import Order, Client, KitBarcodeAssignment, KitCollection
from django.db.models import Q

client = Client.objects.first()
if client:
    print(f"Client: {client.id}")
    orders = Order.objects.filter(
        Q(client_id=client.id) |
        Q(barcode_assignments__client_id=client.id) |
        Q(kit_collection__user_id=client.id)
    ).distinct()
    print(orders)
else:
    print("No client")