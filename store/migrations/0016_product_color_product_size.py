# Generated by Django 5.0.1 on 2024-01-26 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0015_alter_product_star'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='color',
            field=models.TextField(default='', null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='size',
            field=models.TextField(default='', null=True),
        ),
    ]
