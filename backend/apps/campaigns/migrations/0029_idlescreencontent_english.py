from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0028_idlescreencontent_kategori'),
    ]

    operations = [
        migrations.AddField(
            model_name='idlescreencontent',
            name='baslik_en',
            field=models.CharField(blank=True, default='', help_text='Ingilizce idle basligi. Bos = kioskta Turkce basliga geri doner.', max_length=250),
        ),
        migrations.AddField(
            model_name='idlescreencontent',
            name='metin_en',
            field=models.CharField(blank=True, default='', help_text='Ingilizce idle metni. Bos = kioskta Turkce metne geri doner.', max_length=1000),
        ),
    ]
