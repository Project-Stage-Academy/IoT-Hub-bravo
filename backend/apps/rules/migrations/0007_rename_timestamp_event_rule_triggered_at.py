from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rules', '0006_remove_event_idx_events_telemetry_id_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='event',
            name='idx_events_timestamp',
        ),
        migrations.RenameField(
            model_name='event',
            old_name='timestamp',
            new_name='rule_triggered_at',
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['rule_triggered_at'], name='idx_events_rule_triggered_at'),
        ),
    ]
