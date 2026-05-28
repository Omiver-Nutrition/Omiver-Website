from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShippingAddress",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("label", models.CharField(blank=True, max_length=50, help_text="Label like 'Home' or 'Work'")),
                ("street_address", models.CharField(max_length=300)),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("zip_code", models.CharField(blank=True, max_length=20)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shipping_addresses", to="core.client")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
