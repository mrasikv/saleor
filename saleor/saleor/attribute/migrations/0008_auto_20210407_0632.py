# Generated by Django 3.1.7 on 2021-04-07 06:32

from django.db import migrations, models

import saleor.core.db.fields
import saleor.core.utils.editorjs


class Migration(migrations.Migration):
    dependencies = [
        ("attribute", "0007_auto_20210308_1135"),
    ]

    operations = [
        migrations.AddField(
            model_name="attributevalue",
            name="rich_text",
            field=saleor.core.db.fields.SanitizedJSONField(
                blank=True,
                null=True,
                sanitizer=saleor.core.utils.editorjs.clean_editor_js,
            ),
        ),
        migrations.AddField(
            model_name="attributevaluetranslation",
            name="rich_text",
            field=saleor.core.db.fields.SanitizedJSONField(
                blank=True,
                null=True,
                sanitizer=saleor.core.utils.editorjs.clean_editor_js,
            ),
        ),
        migrations.AlterField(
            model_name="attribute",
            name="input_type",
            field=models.CharField(
                choices=[
                    ("dropdown", "Dropdown"),
                    ("multiselect", "Multi Select"),
                    ("file", "File"),
                    ("reference", "Reference"),
                    ("rich-text", "Rich Text"),
                ],
                default="dropdown",
                max_length=50,
            ),
        ),
    ]