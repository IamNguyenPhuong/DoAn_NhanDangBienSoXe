# Generated by Django 4.1.13 on 2025-06-06 12:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parking_management', '0006_alter_perturnticketrules_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='parkinghistory',
            name='VehicleTypeID',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='parking_management.vehicletypes', verbose_name='Loại xe lúc vào'),
        ),
    ]
