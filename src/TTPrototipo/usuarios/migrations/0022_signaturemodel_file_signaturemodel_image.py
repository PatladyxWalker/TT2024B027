# Generated by Django 5.1.2 on 2024-11-28 18:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0021_signaturemodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='signaturemodel',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='signatures/files/'),
        ),
        migrations.AddField(
            model_name='signaturemodel',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='signatures/images/'),
        ),
    ]
