# Generated by Django 5.1.4 on 2024-12-26 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cashbox_app', '0002_alter_secretroom_not_standard_alter_secretroom_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='secretroom',
            name='not_standard',
            field=models.CharField(choices=[('N', 'Наличие галочки'), ('-', 'Отсутствие галочки')], default='-', max_length=5),
        ),
    ]
