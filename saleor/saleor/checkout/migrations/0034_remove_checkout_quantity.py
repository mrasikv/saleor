# Generated by Django 3.1.7 on 2021-04-28 07:01

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0033_checkout_language_code"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="checkout",
            name="quantity",
        ),
    ]