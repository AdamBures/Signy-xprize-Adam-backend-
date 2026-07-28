from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('lessons', '0005_merge_20260726_2218'),
    ]

    operations = [
        migrations.AddField(
            model_name='word',
            name='video_url_en',
            field=models.CharField(
                blank=True,
                default='',
                help_text='English sign-language guide used for English and Czech UI',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='word',
            name='video_url_ru',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Russian sign-language guide used for Russian UI',
                max_length=500,
            ),
        ),
    ]
