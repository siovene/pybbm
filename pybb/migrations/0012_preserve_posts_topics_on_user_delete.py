from django.conf import settings
from django.db import migrations, models

import pybb.models


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0011_post_rejection_reason'),
    ]

    operations = [
        migrations.AlterField(
            model_name='topic',
            name='user',
            field=models.ForeignKey(
                on_delete=models.SET(pybb.models.get_sentinel_user),
                to=settings.AUTH_USER_MODEL,
                verbose_name='User',
            ),
        ),
        migrations.AlterField(
            model_name='post',
            name='user',
            field=models.ForeignKey(
                on_delete=models.SET(pybb.models.get_sentinel_user),
                related_name='posts',
                to=settings.AUTH_USER_MODEL,
                verbose_name='User',
            ),
        ),
    ]
