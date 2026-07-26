from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lessons", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="word",
            name="guidance",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Optional learner guidance: tip, placement and movement",
            ),
        ),
        migrations.AddField(
            model_name="word",
            name="reference_face_metrics",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Expected normalized facial metrics for non-manual markers",
            ),
        ),
        migrations.AddField(
            model_name="word",
            name="requires_face",
            field=models.BooleanField(
                default=False,
                help_text="Whether non-manual facial markers are part of this sign",
            ),
        ),
    ]
