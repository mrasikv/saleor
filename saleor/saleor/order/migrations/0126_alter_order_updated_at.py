# Generated by Django 3.2.12 on 2022-02-09 14:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("order", "0125_populate_order_updated_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
    ]