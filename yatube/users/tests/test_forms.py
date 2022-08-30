from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class UserFormTest(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_creat_user(self):
        """Новый пользователь создается при отправке валидной формы."""
        form_data = {
            'first_name': 'CrateUserTestName',
            'last_name': 'CreateUserTestLastName',
            'email': 'user@testcreate.test',
            'username': 'testcreateuser',
            'password1': '6tfc(IJN123',
            'password2': '6tfc(IJN123',
        }
        response = self.guest_client.post(
            reverse('users:signup'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse('posts:index'))
        created_user = User.objects.get(username=form_data['username'])
        self.assertEqual(created_user.first_name, form_data['first_name'])
        self.assertEqual(created_user.last_name, form_data['last_name'])
        self.assertEqual(created_user.email, form_data['email'])
        self.assertEqual(created_user.username, form_data['username'])
