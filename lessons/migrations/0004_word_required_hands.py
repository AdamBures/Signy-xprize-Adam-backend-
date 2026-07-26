from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lessons", "0003_word_guidance_and_face_markers"),
    ]

    operations = [
        migrations.AddField(
            model_name="word",
            name="required_hands",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Number of hands required for the sign (1 or 2)",
            ),
        ),
    ]
