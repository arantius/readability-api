# Generated by Django 3.1.7 on 2021-04-07 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('readability', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='updated',
            field=models.DateTimeField(),
        ),
    ]
