# Generated by Django 5.0.1 on 2024-01-26 20:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0016_product_color_product_size'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='color',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='product',
            name='size',
            field=models.CharField(default='', max_length=255),
        ),
    ]
