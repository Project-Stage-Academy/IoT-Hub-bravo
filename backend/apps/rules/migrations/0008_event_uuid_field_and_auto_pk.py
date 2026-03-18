"""
Replace UUID primary key with auto-incrementing id.
Existing UUID values are preserved in the new event_uuid field.
"""
import uuid

from django.db import migrations, models


def copy_id_to_event_uuid(apps, schema_editor):
    """Copy existing UUID pk values into the new event_uuid column."""
    Event = apps.get_model('rules', 'Event')
    for event in Event.objects.all():
        Event.objects.filter(pk=event.pk).update(event_uuid=event.pk)


class Migration(migrations.Migration):

    dependencies = [
        ('rules', '0007_rename_timestamp_event_rule_triggered_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='event_uuid',
            field=models.UUIDField(default=uuid.uuid4, null=True),
        ),
        migrations.RunPython(copy_id_to_event_uuid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='event',
            name='event_uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.RemoveField(
            model_name='event',
            name='id',
        ),
        migrations.AddField(
            model_name='event',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
    ]
