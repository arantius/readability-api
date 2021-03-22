# Generated by Django 3.1.7 on 2021-03-21 21:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Feed',
            fields=[
                ('url', models.TextField(primary_key=True, serialize=False)),
                ('title', models.TextField(default=None)),
                ('link', models.TextField(default=None)),
                ('last_fetch_time', models.IntegerField(default=0)),
                ('fetch_interval_seconds', models.IntegerField(default=14400)),
            ],
        ),
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('key', models.TextField(primary_key=True, serialize=False)),
                ('title', models.TextField(default=None)),
                ('link', models.TextField(default=None)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('content', models.TextField(default=None)),
                ('original_content', models.TextField()),
                ('tags', models.JSONField(default=list)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('feed', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='readability.feed')),
            ],
        ),
    ]
