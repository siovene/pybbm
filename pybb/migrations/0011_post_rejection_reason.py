from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0010_topic_hotness_score'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='rejection_reason',
            field=models.CharField(
                verbose_name='Rejection reason',
                max_length=32,
                choices=[
                    ('spam', 'Spam'),
                    ('scam', 'Scam / phishing'),
                    ('harassment', 'Harassment / language / tone'),
                    ('self_promotion', 'Self-promotion'),
                    ('other', 'Other'),
                ],
                null=True,
                blank=True,
                default=None,
            ),
        ),
    ]
