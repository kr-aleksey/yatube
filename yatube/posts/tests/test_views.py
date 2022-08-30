import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, Comment, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mktemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostContextsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='test-user')
        cls.author = User.objects.create_user(username='test-author')
        cls.group = Group.objects.create(
            title='Название группы',
            slug='test-slug',
            description='Тестовая группа'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Текст поста',
            image=uploaded
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Текст комментария'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostContextsTests.author)
        cache.clear()

    def post_test(self, post):
        self.assertIsInstance(post, Post)
        self.assertEqual(post.text, PostContextsTests.post.text)
        self.assertEqual(post.pub_date, PostContextsTests.post.pub_date)
        self.assertEqual(post.author, PostContextsTests.post.author)
        self.assertEqual(post.group, PostContextsTests.post.group)
        self.assertEqual(post.image, PostContextsTests.post.image)


    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        expected_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': PostContextsTests.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': PostContextsTests.author.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostContextsTests.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostContextsTests.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, expected_template in expected_templates.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, expected_template)

    def test_index_context(self):
        """posts:index использует правильный контекст."""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.context['title'],
                         'Последние обновления на сайте')
        self.post_test(response.context['page_obj'][0])

    def test_group_list_context(self):
        """posts:group_list использует правильный контекст."""
        response = self.guest_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': PostContextsTests.group.slug})
        )
        group = response.context.get('group')
        self.assertIsInstance(group, Group)
        self.assertEqual(group, PostContextsTests.group)
        self.post_test(response.context['page_obj'][0])

    def test_profile_context(self):
        """posts:profile использует правильный контекст."""
        author = PostContextsTests.author
        posts_count = Post.objects.filter(author=author).count()
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': author.username})
        )
        self.assertEqual(response.context.get('posts_number'), posts_count)
        self.assertEqual(response.context.get('author'), author)
        self.post_test(response.context['page_obj'][0])

    def test_post_detail_context(self):
        """posts:post_detail использует правильный контекст."""
        url = reverse('posts:post_detail',
                      kwargs={'post_id': PostContextsTests.post.pk})
        response = self.authorized_client.get(url)
        self.post_test(response.context.get('post'))
        form = response.context.get('form')
        form_field_text = form.fields.get('text')
        self.assertTrue(form_field_text, forms.fields.CharField)
        comment = response.context['comments'][0]
        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.text, PostContextsTests.comment.text)

    def test_post_edit_context(self):
        """posts:post_edit использует правильный контекст."""
        url = reverse('posts:post_edit',
                      kwargs={'post_id': PostContextsTests.post.pk})
        response = self.authorized_client.get(url)
        form = response.context.get('form')
        self.post_form_test(form)
        self.assertEqual(form.initial['text'],
                         PostContextsTests.post.text)
        self.assertEqual(form.initial['group'],
                         PostContextsTests.post.group.pk)

    def test_post_create_context(self):
        """posts:post_create использует правильный контекст."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.post_form_test(response.context.get('form'))

    def post_form_test(self, form):
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field, expected)


class PostFiltersTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test-user')
        cls.author = User.objects.create_user(username='test-author')
        cls.group = Group.objects.create(
            title='Название группы',
            slug='group-slug',
            description='Группа для тестирования отображения поста '
        )
        cls.group_without_posts = Group.objects.create(
            title='Группа без постов',
            slug='group-without-posts',
            description='Для проверки фильтра постов по slug'
        )
        cls.group_post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Пост для тестирования отображения на странице.'
        )
        Post.objects.create(
            author=cls.user,
            text='Этот пост не должен попасть в фильтры.'
        )
        Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Попадет группу. Не попадет в профайл.'
        )

    def setUp(self):
        self.guest_client = Client()
        cache.clear()

    def test_post_display(self):
        """Созданный пост отображается на страницах."""
        author = PostFiltersTests.author
        group = PostFiltersTests.group
        url_post_counts = {
            reverse('posts:index'): Post.objects.count(),
            reverse('posts:profile', kwargs={'username': author.username}):
                Post.objects.filter(author=author).count(),
            reverse('posts:group_list', kwargs={'slug': group.slug}):
                Post.objects.filter(group=group).count(),
        }
        for url, post_count in url_post_counts.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(len(response.context['page_obj']), post_count)

    def test_post_not_display_in_other_group(self):
        """Пост не попадает в другие группы"""
        group = PostFiltersTests.group_without_posts
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': group.slug})
        )
        self.assertEqual(len(response.context['page_obj']), 0)


class PostPaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='pg-author')
        cls.group = Group.objects.create(
            title='Группа paginator',
            description='Группа для тестирования paginator',
            slug='for-paginator-test'
        )
        post = Post(
            author=cls.author,
            group=cls.group,
            text='Тест paginator'
        )
        posts = [post] * (settings.POSTS_LIMIT + 1)
        Post.objects.bulk_create(posts)

    def setUp(self):
        self.guest_client = Client()
        cache.clear()

    def test_paginator(self):
        """Paginator работает правильно"""
        author = PostPaginatorTest.author
        group = PostPaginatorTest.group
        urls = (
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': author.username}),
            reverse('posts:group_list', kwargs={'slug': group.slug}),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']),
                    settings.POSTS_LIMIT,
                    'Неверное количество постов на первой странице.'
                )
                response = self.guest_client.get(url + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    1,
                    'Неверное количество постов на последней странице.'
                )


class PostCatchTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test-user')
        cls.post = Post.objects.create(author=cls.user,
                                       text='Text for test cache')

    def setUp(self):
        self.guest_client = Client()
        cache.clear()

    def test_catch_index_page(self):
        """После удаления пост остается в кэше."""
        response = self.guest_client.get(reverse('posts:index'))
        post_text = PostCatchTests.post.text
        self.assertContains(response, post_text)
        PostCatchTests.post.delete()
        response = self.guest_client.get(reverse('posts:index'))
        self.assertContains(response, post_text)


class PostFollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_follower = User.objects.create_user(username='user-follower')
        cls.user_not_follower = User.objects.create_user(
            username='user-not-follower'
        )
        cls.author = User.objects.create_user(username='author')
        author_without_followers = User.objects.create_user(
            username='author-wof'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Пост автора с подписчиками'
        )
        Post.objects.create(
            author=author_without_followers,

            text='Пост автора без подписчиков')
        cls.follow = Follow.objects.create(
            author=cls.author,
            user=cls.user_follower
        )

    def setUp(self):
        self.follower_client = Client()
        self.follower_client.force_login(PostFollowTests.user_follower)
        self.not_follower_client = Client()
        self.not_follower_client.force_login(PostFollowTests.user_not_follower)
        cache.clear()

    def test_display_post_in_follower_feed(self):
        """Отображение поста в ленте подписчика."""
        response = self.follower_client.get(reverse('posts:follow_index'))
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 1)
        self.assertIsInstance(page_obj[0], Post)
        self.assertEqual(page_obj[0], PostFollowTests.post)

    def test_not_display_post_in_not_follower_feed(self):
        """Отсутствие поста в ленте не подписанного пользователя."""
        response = self.not_follower_client.get(reverse('posts:follow_index'))
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 0)

    def test_follow_and_unfollow(self):
        """Добавление и удаление подписки."""
        author = PostFollowTests.author
        user = PostFollowTests.user_not_follower
        self.assertFalse(Follow.objects.filter(author=author, user=user)
                         .exists())
        self.not_follower_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': author.username})
        )
        self.assertTrue(Follow.objects.filter(author=author, user=user)
                        .exists())
        self.not_follower_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': author.username})
        )
        self.assertFalse(Follow.objects.filter(author=author, user=user)
                         .exists())
