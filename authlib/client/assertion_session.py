from requests import Session
from ..specs.rfc6749 import OAuth2Token
from ..specs.rfc7523 import JWTBearerGrant
from .oauth2_auth import OAuth2Auth


class AssertionSession(Session):
    """Constructs a new Assertion Framework for OAuth 2.0 Authorization Grants
    per RFC7521_.

    .. _RFC7521: https://tools.ietf.org/html/rfc7521
    """
    JWT_BEARER_GRANT_TYPE = JWTBearerGrant.GRANT_TYPE

    ASSERTION_METHODS = {
        JWT_BEARER_GRANT_TYPE: JWTBearerGrant.sign,
    }

    def __init__(self, token_url, issuer, subject, audience, grant_type,
                 claims=None, token_placement='header', scope=None, **kwargs):
        super(AssertionSession, self).__init__()
        self.token_url = token_url
        self.grant_type = grant_type

        # https://tools.ietf.org/html/rfc7521#section-5.1
        self.issuer = issuer
        self.subject = subject
        self.audience = audience
        self.claims = claims
        self.scope = scope
        self._token_auth = OAuth2Auth(None, token_placement)
        self._kwargs = kwargs

    @property
    def token(self):
        return self._token_auth.token

    @token.setter
    def token(self, token):
        self._token_auth.token = OAuth2Token.from_dict(token)

    def auto_refresh_token(self):
        """Refresh token automatically."""
        if not self.token or self.token.is_expired():
            self.refresh_token()

    def refresh_token(self):
        """Using Assertions as Authorization Grants to refresh token as
        described in `Section 4.1`_.

        .. _`Section 4.1`: https://tools.ietf.org/html/rfc7521#section-4.1
        """
        generate_assertion = self.ASSERTION_METHODS[self.grant_type]
        assertion = generate_assertion(
            issuer=self.issuer,
            subject=self.subject,
            audience=self.audience,
            claims=self.claims,
            **self._kwargs
        )
        data = {'assertion': assertion, 'grant_type': self.grant_type}
        if self.scope:
            data['scope'] = self.scope
        resp = self.request('POST', self.token_url, data=data, withhold_token=True)
        self.token = resp.json()
        return self.token

    def request(self, method, url, data=None, headers=None,
                withhold_token=False, auth=None, **kwargs):
        """Send request with auto refresh token feature."""
        if not withhold_token:
            self.auto_refresh_token()

            if auth is None:
                auth = self._token_auth
        return super(AssertionSession, self).request(
            method, url, headers=headers, data=data, auth=auth, **kwargs)
