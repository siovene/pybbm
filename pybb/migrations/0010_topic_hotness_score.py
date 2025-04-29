# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0009_topic_images'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='hotness_score',
            field=models.FloatField(default=0, verbose_name='Hotness score', db_index=True),
        ),
    ]