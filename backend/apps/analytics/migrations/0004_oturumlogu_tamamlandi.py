from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_delete_reklamgosterim'),
    ]

    operations = [
        migrations.AddField(
            model_name='oturumlogu',
            name='tamamlandi',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'True = kullanici akisi tamamladi (QR uretildi). '
                    'False = 10sn etkilesimsizlik ile terk edilmis (sahte/abandoned oturum).'
                ),
            ),
        ),
    ]
