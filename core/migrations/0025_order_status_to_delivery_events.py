"""Replace Order.status with a fold over DeliveryEvent rows.

The column is dropped, so the stored status of every existing order is
translated into the delivery event that implies it *before* the schema change.
Without this backfill, in-flight orders would silently reset to "CREATED".

The reverse migration restores the column and recomputes a status from the
events, so the change is not a one-way door.
"""

from django.db import migrations, models


# Legacy Order.status value -> the event(s) that now represent it.
#
# Several legacy statuses described the *sample*, not the parcel: an order that
# was TESTING or FINISHED means the lab already had the sample, which in the
# new model is the end of the return leg.
STATUS_TO_EVENTS = {
    "CREATED": ["ORDER_PLACED"],
    "PENDING": ["ORDER_PLACED"],          # never a valid choice, but present in data
    "CONFIRMED": ["ORDER_PLACED"],
    "SHIPPED": ["ORDER_PLACED", "SHIPPED"],
    "IN_TRANSIT": ["ORDER_PLACED", "IN_TRANSIT"],
    "OUT_FOR_DELIVERY": ["ORDER_PLACED", "OUT_FOR_DELIVERY"],
    "DELIVERED": ["ORDER_PLACED", "SHIPPED", "DELIVERED"],
    "COLLECTED": ["ORDER_PLACED", "SHIPPED", "DELIVERED"],
    "TESTING": ["ORDER_PLACED", "SHIPPED", "DELIVERED", "SAMPLE_SHIPPED", "SAMPLE_DELIVERED"],
    "FINISHED": ["ORDER_PLACED", "SHIPPED", "DELIVERED", "SAMPLE_SHIPPED", "SAMPLE_DELIVERED"],
    "CANCELLED": ["ORDER_PLACED", "CANCELLED"],
}

EVENT_TITLES = {
    "ORDER_PLACED": ("Order Placed", "Your order has been received"),
    "SHIPPED": ("Shipped", "Your kit is on its way"),
    "IN_TRANSIT": ("In Transit", "Your kit is in transit"),
    "OUT_FOR_DELIVERY": ("Out for Delivery", "Your kit is out for delivery"),
    "DELIVERED": ("Delivered", "Your kit has been delivered"),
    "SAMPLE_SHIPPED": ("Sample Shipped", "Your sample is on its way to the laboratory"),
    "SAMPLE_DELIVERED": ("Sample Delivered", "Your sample has arrived at the laboratory"),
    "CANCELLED": ("Order Cancelled", "Your order has been cancelled"),
}

# Rank used to recompute a status when migrating backwards.
REVERSE_RANK = [
    "ORDER_PLACED",
    "SHIPPED",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "SAMPLE_SHIPPED",
    "SAMPLE_DELIVERED",
]


def backfill_events(apps, schema_editor):
    Order = apps.get_model("core", "Order")
    DeliveryEvent = apps.get_model("core", "DeliveryEvent")

    for order in Order.objects.all().iterator():
        existing = set(
            DeliveryEvent.objects.filter(order=order).values_list("event_type", flat=True)
        )
        wanted = STATUS_TO_EVENTS.get(order.status, ["ORDER_PLACED"])

        for event_type in wanted:
            if event_type in existing:
                continue
            title, description = EVENT_TITLES[event_type]
            DeliveryEvent.objects.create(
                order=order,
                event_type=event_type,
                title=title,
                description=description,
                is_completed=event_type != "CANCELLED",
            )


def restore_status(apps, schema_editor):
    """Recompute a stored status from the events (used on reverse)."""
    Order = apps.get_model("core", "Order")
    DeliveryEvent = apps.get_model("core", "DeliveryEvent")

    for order in Order.objects.all().iterator():
        types = list(
            DeliveryEvent.objects.filter(order=order).values_list("event_type", flat=True)
        )
        if "CANCELLED" in types:
            order.status = "CANCELLED"
        else:
            ranked = [REVERSE_RANK.index(t) for t in types if t in REVERSE_RANK]
            order.status = REVERSE_RANK[max(ranked)] if ranked else "CREATED"
        order.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_kitcollection_step_progress"),
    ]

    operations = [
        # Widen the choices first so the backfill can write the new types.
        migrations.AlterField(
            model_name="deliveryevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("ORDER_PLACED", "Order Placed"),
                    ("SHIPPED", "Shipped"),
                    ("IN_TRANSIT", "In Transit"),
                    ("OUT_FOR_DELIVERY", "Out for Delivery"),
                    ("DELIVERED", "Delivered"),
                    ("SAMPLE_SHIPPED", "Sample Shipped"),
                    ("SAMPLE_DELIVERED", "Sample Delivered"),
                    ("CANCELLED", "Cancelled"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_events, restore_status),
        migrations.RemoveField(
            model_name="order",
            name="status",
        ),
    ]
