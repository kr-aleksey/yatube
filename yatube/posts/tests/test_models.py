from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг группы',
            description='Описание тестовой группы'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=('Текст тестового поста. В два предложения.'
                  'Может быть даже в три и более. Мало ли что?')
        )

    def test_models_have_correct_object_names(self):
        """Метод str моделей возвращает корректный результат."""
        group = PostModelTest.group
        post = PostModelTest.post
        object_names = {
            group: group.title,
            post: post.text[:15],
        }
        for test_object, expected_value in object_names.items():
            with self.subTest(test_object=test_object):
                self.assertEqual(str(test_object), expected_value)
                str(test_object), expected_value

    def test_post_verbose_name(self):
        post = PostModelTest.post
        field_verbose_names = {
            'text': 'Текст поста',
            'group': 'Группа'
        }
        for field, expected_value in field_verbose_names.items():
            with self.subTest(field=field):
                self.assertEqual(post._meta.get_field(field).verbose_name,
                                 expected_value)

    def test_post_help_text(self):
        """help_text полей совпадает с ожидаемым"""
        field_help_texts = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост',
        }
        for field, expected_value in field_help_texts.items():
            post = PostModelTest.post
            with self.subTest(field=field):
                self.assertEqual(post._meta.get_field(field).help_text,
                                 expected_value)
