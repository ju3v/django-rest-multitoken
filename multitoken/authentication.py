from django.utils.translation import ugettext_lazy as _
from rest_framework import authentication, exceptions
from . import models


class TokenAuthentication(authentication.TokenAuthentication):
    model = models.Token

    def authenticate_credentials(self, key):
        token_user, token = super(
            TokenAuthentication, self).authenticate_credentials(key)
        if token.is_expired:
            raise exceptions.AuthenticationFailed(_('invalid_token'))
        return token_user, token
