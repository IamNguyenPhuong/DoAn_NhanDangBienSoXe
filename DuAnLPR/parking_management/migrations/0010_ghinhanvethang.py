# Generated by Django 4.1.13 on 2025-06-13 03:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parking_management', '0009_remove_parkinghistory_perturnruleappliedid_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GhiNhanVeThang',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purchase_date', models.DateField(auto_now_add=True, verbose_name='Ngày mua')),
                ('expiry_date', models.DateField(verbose_name='Ngày hết hạn')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Số tiền đã trả')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='parking_management.vehicle', verbose_name='Xe đăng ký')),
            ],
            options={
                'verbose_name': 'Ghi nhận vé tháng',
                'verbose_name_plural': 'Các ghi nhận vé tháng',
                'ordering': ['-purchase_date'],
            },
        ),
    ]
