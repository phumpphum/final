# Generated by Django 5.0.3 on 2025-03-18 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('food', '0007_orderitem_created_at_orderitem_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
