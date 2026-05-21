"""Add forward and return tracking numbers to Order

Revision ID: order_forward_and_return_tracking_number
Revises: 0019_remove_pricingtier
Create Date: 2026-05-21 00:20
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_remove_pricingtier"),
    ]

    operations = [
        migrations.RenameField(
            model_name="order",
            old_name="tracking_number",
            new_name="forward_tracking_number",
        ),
        migrations.AddField(
            model_name="order",
            name="return_tracking_number",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
    ]
