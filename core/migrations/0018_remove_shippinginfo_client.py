"""Remove client field from ShippingInfo

Revision ID: remove_shippinginfo_client
Revises: 0017_shippinginfo_order
Create Date: 2026-05-21 00:00
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_shippinginfo_order"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="shippinginfo",
            name="client",
        ),
    ]
