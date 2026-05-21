"""Remove PricingTier model

Revision ID: remove_pricingtier
Revises: 0018_remove_shippinginfo_client
Create Date: 2026-05-21 00:10
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_remove_shippinginfo_client"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PricingTier",
        ),
    ]
