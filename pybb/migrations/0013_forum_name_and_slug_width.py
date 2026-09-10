from django.db import migrations, models


def refuse_lossy_reverse(apps, schema_editor):
    # PostgreSQL is the deployment backend. The retained-lock guarantee is
    # specific to its transactional DDL; other vendors only get the length check.
    connection = schema_editor.connection
    forum = apps.get_model('pybb', 'Forum')
    table = connection.ops.quote_name(forum._meta.db_table)
    name = connection.ops.quote_name('name')
    slug = connection.ops.quote_name('slug')
    with connection.cursor() as cursor:
        if connection.vendor == 'postgresql':
            if not connection.in_atomic_block:
                raise RuntimeError('Forum width reversal requires an atomic migration')
            # Keep the explicit lock through both subsequent reverse AlterFields.
            # Django emits an explicit USING column::varchar(n) narrowing cast,
            # which PostgreSQL permits to truncate long values silently.
            cursor.execute('LOCK TABLE {} IN ACCESS EXCLUSIVE MODE'.format(table))
        cursor.execute('SELECT 1 FROM {} WHERE LENGTH({}) > 128 OR LENGTH({}) > 255 LIMIT 1'.format(
            table, name, slug))
        if cursor.fetchone():
            raise RuntimeError('Cannot reverse forum widths: a name exceeds 128 characters or a slug exceeds 255. '
                               'Resolve those values explicitly before retrying.')


class Migration(migrations.Migration):
    dependencies = [
        ('pybb', '0012_preserve_posts_topics_on_user_delete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='forum', name='name',
            field=models.CharField(max_length=512, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='forum', name='slug',
            field=models.SlugField(max_length=512, verbose_name='Slug'),
        ),
        # The check runs first on reverse, under the same migration transaction.
        migrations.RunPython(migrations.RunPython.noop, reverse_code=refuse_lossy_reverse),
    ]
