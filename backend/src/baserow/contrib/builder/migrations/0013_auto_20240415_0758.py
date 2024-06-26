# Generated by Django 4.1.13 on 2024-04-15 07:58

from django.db import migrations


def migrate_wf_actions(apps, schema_editor):
    OpenPageWorkflowAction = apps.get_model("builder", "openpageworkflowaction")
    actions = OpenPageWorkflowAction.objects.all()
    for action in actions:
        action.navigate_to_url = action.url
        action.navigation_type = "custom"
        action.navigate_to_page_id = None
        action.page_parameters = []
        action.target = "self"
        action.save()


def migrate_collection_links(apps, schema_editor):
    CollectionField = apps.get_model("builder", "CollectionField")
    fields = CollectionField.objects.filter(type="link")
    for field in fields:
        field.target = "self"
        field.save()


class Migration(migrations.Migration):
    dependencies = [
        ("builder", "0012_openpageworkflowaction_navigate_to_page_and_more"),
    ]

    operations = [
        migrations.RunPython(
            migrate_wf_actions, reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            migrate_collection_links, reverse_code=migrations.RunPython.noop
        ),
    ]
