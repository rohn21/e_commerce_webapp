# Generated by Django 5.1.5 on 2025-02-20 04:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_shippingmethod_order_address_alter_coupon_table_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='tracking_number',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
