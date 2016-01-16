"""Imports"""
import tweepy


class TwitterBot:
    def __init__(self, consumer_key, consumer_secret,
                 access_token, access_token_secret):
        self.auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self.auth.secure = False
        self.auth.set_access_token(access_token, access_token_secret)

    def is_authenticated(self, api=None):
        """Checks if it is/can authenticate successfully"""
        if not api:
            api = self.authenticate()
        if api.me().name:
            return True
        return False

    def authenticate(self, auth=None):
        """Authenticate with Twitter using the existing keys"""
        if not auth:
            auth = self.auth
        return tweepy.API(auth)

    def post(self, status):
        """Posts to Twitter using the provided string"""
        api = self.authenticate()
        if self.is_authenticated(api):
            response = api.update_status(status=status)
            if response:
                print 'tweet attempted'
                user = response.user
                name = user.name
                id = response.id_str
                return 'https://twitter.com/{}/status/{}'.format(name, id)
