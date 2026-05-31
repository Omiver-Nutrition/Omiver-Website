from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_remove_kitbarcodeassignment_order_number_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="kitbarcodeassignment",
            name="collected_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]