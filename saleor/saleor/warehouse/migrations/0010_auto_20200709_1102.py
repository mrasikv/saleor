# Generated by Django 3.0.6 on 2020-07-09 11:02

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0009_remove_invalid_allocation"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="warehouse",
            options={"ordering": ("-slug",)},
        ),
    ]