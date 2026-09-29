from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_add_danisma_sira'),
    ]

    operations = [
        migrations.AddField(
            model_name='kategori',
            name='ad_en',
            field=models.CharField(blank=True, default='', help_text='Ingilizce kategori adi. Bos = kioskta Turkce ada geri doner.', max_length=200),
        ),
        migrations.AddField(
            model_name='danisma',
            name='ad_en',
            field=models.CharField(blank=True, default='', help_text='Ingilizce danisma kategori adi. Bos = kioskta Turkce ada geri doner.', max_length=200),
        ),
        migrations.AddField(
            model_name='soru',
            name='metin_en',
            field=models.TextField(blank=True, default='', help_text='Ingilizce soru metni. Bos = kioskta Turkce metne geri doner.'),
        ),
        migrations.AddField(
            model_name='cevap',
            name='metin_en',
            field=models.CharField(blank=True, default='', help_text='Ingilizce cevap metni. Bos = kioskta Turkce metne geri doner.', max_length=255),
        ),
    ]
