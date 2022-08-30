# Generated by Django 2.2.16 on 2022-08-26 13:15

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('posts', '0009_follow'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='follow',
            unique_together={('user', 'author')},
        ),
    ]
