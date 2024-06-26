# Generated by Django 4.1.13 on 2024-05-10 14:46

from django.db import migrations


def forward(apps, schema_editor):
    CollectionField = apps.get_model("builder", "CollectionField")
    fields = CollectionField.objects.filter(type="link")

    migrated_fields = []
    for field in fields:
        if "page_parameters" not in field.config:
            field.config["page_parameters"] = []
            migrated_fields.append(field)
        if "target" not in field.config:
            field.config["target"] = "self"
            migrated_fields.append(field)

    CollectionField.objects.bulk_update(migrated_fields, ["config"])


class Migration(migrations.Migration):
    dependencies = [
        ("builder", "0017_repeatelement"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
