# Generated by Django 5.1.2 on 2024-11-19 05:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0014_contrato_fotos_subidas_anfitrion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='cancelado',
            field=models.BooleanField(default=False),
        ),
    ]