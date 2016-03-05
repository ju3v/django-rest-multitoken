import datetime
import freezegun

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.test import override_settings
from djet import assertions, restframework, utils
from rest_framework import status
from multitoken import models, views


def create_user(**kwargs):
    data = {
        'username': 'john',
        'password': 'secret',
        'email': 'john@beatles.com',
    }
    data.update(kwargs)
    user = get_user_model().objects.create_user(**data)
    user.raw_password = data['password']
    return user


class LoginViewTest(restframework.APIViewTestCase,
                    assertions.StatusCodeAssertionsMixin,
                    assertions.InstanceAssertionsMixin):
    view_class = views.ObtainTokenView

    def setUp(self):
        self.signal_sent = False

    def signal_receiver(self, *args, **kwargs):
        self.signal_sent = True

    def test_post_should_login_user(self):
        user = create_user()
        data = {
            'username': user.username,
            'password': user.raw_password,
            'client': 'my-device',
        }
        user_logged_in.connect(self.signal_receiver)
        request = self.factory.post(data=data)

        response = self.view(request)

        self.assert_status_equal(response, status.HTTP_200_OK)
        token = user.auth_tokens.get()
        self.assertEqual(response.data['auth_token'], token.key)
        self.assertEqual(data['client'], token.client)
        self.assertTrue(self.signal_sent)

    def test_post_should_not_login_inactive_user(self):
        user = create_user()
        data = {
            'username': user.username,
            'password': user.raw_password,
            'client': 'my-device',
        }
        user.is_active = False
        user.save()
        user_logged_in.connect(self.signal_receiver)
        request = self.factory.post(data=data)

        response = self.view(request)

        self.assert_status_equal(response, status.HTTP_400_BAD_REQUEST)
        with self.assertRaises(models.Token.DoesNotExist):
            user.auth_tokens.get()
        self.assertFalse(self.signal_sent)

    def test_post_should_not_login_when_wrong_credentials(self):
        user = create_user()
        data = {
            'username': 'wrong username',
            'password': 'wrong password',
            'client': 'my-device',
        }
        user_logged_in.connect(self.signal_receiver)
        request = self.factory.post(data=data)

        response = self.view(request)

        self.assert_status_equal(response, status.HTTP_400_BAD_REQUEST)
        with self.assertRaises(models.Token.DoesNotExist):
            user.auth_tokens.get()
        self.assertFalse(self.signal_sent)


class LogoutViewTest(restframework.APIViewTestCase,
                     assertions.StatusCodeAssertionsMixin):
    view_class = views.InvalidateTokenView

    def test_post_should_logout_logged_in_user(self):
        user = create_user()
        token = models.Token.objects.create(user=user, client='my-device')

        request = self.factory.post(user=user, token=token)
        response = self.view(request)

        self.assert_status_equal(response, status.HTTP_200_OK)
        self.assertEqual(response.data, None)
        with self.assertRaises(models.Token.DoesNotExist):
            utils.refresh(token)

    def test_post_should_deny_logging_out_when_user_not_logged_in(self):
        create_user()

        request = self.factory.post()
        response = self.view(request)

        self.assert_status_equal(response, status.HTTP_401_UNAUTHORIZED)

    @freezegun.freeze_time("2015-01-01")
    @override_settings(
        REST_MULTITOKEN={'TOKEN_TIMEOUT': datetime.timedelta(days=1)})
    def test_post_should_not_login_user_with_expired_token(self):
        user = create_user()
        token = models.Token.objects.create(
            user=user,
            client='my-device',
            created=datetime.datetime.utcnow() - datetime.timedelta(days=2))

        data = {
            'username': user.username,
            'password': user.raw_password,
            'client': 'my-device',
        }
        request = self.factory.post(data=data)

        response = self.view(request)

        self.assert_status_equal(response, status.HTTP_401_UNAUTHORIZED)
