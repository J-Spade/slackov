import tweepy

class TwitterBot:
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.secure = False
        auth.set_access_token(access_token, access_token_secret)

        self.api = tweepy.API(auth)

        # If the authentication was successful, you should
        # see the name of the account print out
        if self.isActivated():
            print 'TWITTER SUCCESSFULLY AUTHENTICATED'
        else:
            print 'TWITTER COULD NOT AUTHENTICATE'

    def isActivated(self):
        if self.api.me().name:
            return True
        return False

    def post(self, status):
        if self.isActivated():
            status = self.api.update_status(status=status)

