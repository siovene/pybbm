# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.test import TestCase

from pybb import defaults
from pybb.models import Category, Forum, Topic, create_or_check_slug


@contextmanager
def duplicate_limit(value):
    before = defaults.PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT
    defaults.PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT = value
    try:
        yield
    finally:
        defaults.PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT = before


class ForumWidthTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Forum width tests')

    def test_long_title_and_generated_slug_are_preserved_exactly(self):
        name = 'x' * 512
        forum = Forum.objects.create(category=self.category, name=name)
        forum.refresh_from_db()
        self.assertEqual(name, forum.name)
        self.assertEqual(name, forum.slug)
        self.assertEqual(512, Forum._meta.get_field('name').max_length)
        self.assertEqual(512, Forum._meta.get_field('slug').max_length)
        self.assertTrue(Forum._meta.get_field('slug').db_index)

    def test_normalization_expansion_uses_each_models_declared_slug_width(self):
        # Each Roman numeral normalizes to four ASCII characters (VIII).
        forum = Forum.objects.create(category=self.category, name='Ⅷ' * 512)
        category = Category.objects.create(name='Ⅷ' * 80)
        topic = Topic(name='Ⅷ' * 255)
        self.assertEqual('viii' * 128, forum.slug)
        self.assertEqual(('viii' * 80)[:255], category.slug)
        self.assertEqual(('viii' * 255)[:255], create_or_check_slug(topic, Topic))
        self.assertEqual('Ⅷ' * 512, forum.name)
        self.assertEqual('Ⅷ' * 80, category.name)

    def test_collision_suffixes_fit_across_counter_digit_boundary(self):
        with duplicate_limit(100):
            forums = [Forum.objects.create(category=self.category, name='x' * 512) for _ in range(12)]
        self.assertEqual('x' * 512, forums[0].slug)
        self.assertEqual('x' * 510 + '-9', forums[9].slug)
        self.assertEqual('x' * 509 + '-10', forums[10].slug)
        self.assertEqual(12, len({forum.slug for forum in forums}))
        self.assertTrue(all(len(forum.slug) == 512 for forum in forums))

    def test_different_long_tails_do_not_lose_their_identity(self):
        first = Forum.objects.create(category=self.category, name='x' * 510 + 'aa')
        second = Forum.objects.create(category=self.category, name='x' * 510 + 'bb')
        self.assertEqual(first.name, first.slug)
        self.assertEqual(second.name, second.slug)
        self.assertNotEqual(first.slug, second.slug)

    def test_existing_explicit_url_survives_title_changes(self):
        forum = Forum.objects.create(category=self.category, name='First', slug='keep-' + 's' * 507)
        old_slug = forum.slug
        forum.name = 'Ⅷ' * 512
        forum.save()
        forum.refresh_from_db()
        self.assertEqual(old_slug, forum.slug)

    def test_short_titles_and_global_slug_collision_scope_are_preserved(self):
        first = Forum.objects.create(category=self.category, name='Existing short title')
        other_category = Category.objects.create(name='Another category')
        second = Forum.objects.create(category=other_category, name=first.name)
        self.assertEqual('existing-short-title', first.slug)
        # Existing PyBB signals check forum slugs globally, even across categories.
        self.assertEqual('existing-short-title-1', second.slug)

    def test_category_clipping_disambiguates_collisions_and_preserves_existing_urls(self):
        first = Category.objects.create(name='㎯' * 79 + 'a')
        second = Category.objects.create(name='㎯' * 79 + 'b')
        self.assertEqual(('rads2' * 79)[:255], first.slug)
        self.assertEqual(first.slug[:253] + '-1', second.slug)
        existing = second.slug
        second.name = 'Changed category title'
        second.save()
        second.refresh_from_db()
        self.assertEqual(existing, second.slug)

    def test_topic_save_clipping_collision_and_explicit_forum_filter(self):
        from pybb.compat import get_user_model
        user = get_user_model().objects.create_user(username='forum-width-topics')
        forum = Forum.objects.create(category=self.category, name='Topic clipping')
        first = Topic.objects.create(forum=forum, user=user, name='㎯' * 254 + 'a')
        second = Topic.objects.create(forum=forum, user=user, name='㎯' * 254 + 'b')
        self.assertEqual(('rads2' * 254)[:255], first.slug)
        self.assertEqual(first.slug[:253] + '-1', second.slug)
        existing = second.slug
        second.name = 'Changed topic title'
        second.save()
        second.refresh_from_db()
        self.assertEqual(existing, second.slug)
        # Current signals use global collision scope for all three models.
        # The helper also supports an explicit scope; keep that API working.
        other = Forum.objects.create(category=self.category, name='Other topics')
        candidate = Topic(forum=other, user=user, name='㎯' * 254 + 'c')
        self.assertEqual(first.slug, create_or_check_slug(candidate, Topic, forum=other))
        self.assertEqual(first.slug[:253] + '-2', create_or_check_slug(candidate, Topic))

    def test_migration_fields_match_models_and_forward_is_noop(self):
        import importlib
        from django.db import migrations
        from django.utils.translation import override
        module = importlib.import_module('pybb.migrations.0013_forum_name_and_slug_width')
        migration = module.Migration('0013_forum_name_and_slug_width', 'pybb')
        self.assertEqual([('pybb', '0012_preserve_posts_topics_on_user_delete')], migration.dependencies)
        alters = migration.operations[:2]
        self.assertEqual([('forum', 'name'), ('forum', 'slug')],
                         [(operation.model_name, operation.name) for operation in alters])
        with override('en'):
            for operation in alters:
                self.assertIsInstance(operation, migrations.AlterField)
                self.assertEqual(Forum._meta.get_field(operation.name).deconstruct()[1:],
                                 operation.field.deconstruct()[1:])
        self.assertEqual(3, len(migration.operations))
        self.assertIs(migrations.RunPython.noop, migration.operations[2].code)
        self.assertIs(module.refuse_lossy_reverse, migration.operations[2].reverse_code)

    def test_duplicate_limit_refuses_without_creating_a_row(self):
        first = Forum.objects.create(category=self.category, name='Duplicate')
        with duplicate_limit(1):
            with self.assertRaises(ValidationError):
                Forum.objects.create(category=self.category, name='Duplicate')
        self.assertEqual([first.pk], list(Forum.objects.values_list('pk', flat=True)))
