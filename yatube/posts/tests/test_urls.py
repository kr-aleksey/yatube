from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test-user')
        cls.author = User.objects.create_user(username='test-author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group-slug',
            description='Описание тестовой группы'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Текст поста'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        self.author_client = Client()
        self.author_client.force_login(PostURLTests.author)
        cache.clear()

    def test_url_guest_access(self):
        """Доступность url для неавторизованного пользователя."""
        expected_statuses = {
            '/': HTTPStatus.OK,
            '/follow/': HTTPStatus.FOUND,
            f'/group/{PostURLTests.group.slug}/': HTTPStatus.OK,
            f'/profile/{PostURLTests.author.username}/': HTTPStatus.OK,
            f'/profile/{PostURLTests.author.username}/follow/':
                HTTPStatus.FOUND,
            f'/profile/{PostURLTests.author.username}/unfollow/':
                HTTPStatus.FOUND,
            f'/posts/{PostURLTests.post.pk}/': HTTPStatus.OK,
            f'/posts/{PostURLTests.post.pk}/edit/': HTTPStatus.FOUND,
            f'/posts/{PostURLTests.post.pk}/comment/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for url, expected_status in expected_statuses.items():
            with self.subTest(url=url):
                requests = self.guest_client.get(url)
                self.assertEqual(requests.status_code, expected_status)

    def test_url_authorized_access(self):
        """Доступность url для авторизованного пользователя"""
        expected_statuses = {
            f'/posts/{PostURLTests.post.pk}/edit/': HTTPStatus.FOUND,
            f'/posts/{PostURLTests.post.pk}/comment/': HTTPStatus.FOUND,
            f'/profile/{PostURLTests.author.username}/follow/':
                HTTPStatus.FOUND,
            f'/profile/{PostURLTests.author.username}/unfollow/':
                HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
        }
        for url, expected_status in expected_statuses.items():
            with self.subTest(url=url):
                request = self.authorized_client.get(url)
                self.assertEqual(request.status_code, expected_status)

    def test_url_access_for_author(self):
        """Доступ к станице редактирования для автора поста."""
        response = self.author_client.get(
            f'/posts/{PostURLTests.post.pk}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_authorized(self):
        """Редирект для авторизованных пользователей."""
        post = PostURLTests.post

        url_redirect = {
            f'/posts/{post.pk}/comment/': f'/posts/{post.pk}/',
            f'/profile/{PostURLTests.author.username}/follow/':
                f'/profile/{PostURLTests.author.username}/',
            f'/profile/{PostURLTests.author.username}/unfollow/':
                f'/profile/{PostURLTests.author.username}/',
        }
        for url, redirect_url in url_redirect.items():
            response = self.authorized_client.get(url, follow=True)
            with self.subTest(url=url):
                self.assertRedirects(response, redirect_url)

    def test_redirect_guest_to_login_page(self):
        """Редирект для неавторизованного пользователя."""
        post = PostURLTests.post
        urls = (
            '/create/',
            f'/posts/{post.pk}/edit/',
            f'/posts/{post.pk}/comment/',
            f'/profile/{PostURLTests.author.username}/follow/',
            f'/profile/{PostURLTests.author.username}/unfollow/',
        )
        for url in urls:
            expected_redirect = f'/auth/login/?next={url}'
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, expected_redirect)

    def test_uses_correct_templates(self):
        """Используется соответствующий шаблон."""
        expected_templates = {
            '/': 'posts/index.html',
            '/follow/': 'posts/follow.html',
            f'/group/{PostURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostURLTests.author.username}/': 'posts/profile.html',
            f'/posts/{PostURLTests.post.pk}/': 'posts/post_detail.html',
            f'/posts/{PostURLTests.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
        }
        for url, expected_template in expected_templates.items():
            with self.subTest(url=url, template=expected_template):
                response = self.author_client.get(url)
                self.assertTemplateUsed(response, expected_template)
