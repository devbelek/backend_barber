# Generated by Django 5.2 on 2025-05-15 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='bio',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='location_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='longitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='specialization',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='working_days',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='working_hours_from',
            field=models.TimeField(default='09:00'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='working_hours_to',
            field=models.TimeField(default='18:00'),
        ),
    ]
