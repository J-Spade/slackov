"""Imports"""
import tweepy
import re


class TwitterBot:
    def __init__(self, consumer_key, consumer_secret,
                 access_token, access_token_secret):
        self.auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self.auth.secure = False
        self.auth.set_access_token(access_token, access_token_secret)
        api = self.authenticate(self.auth)
        if self.is_authenticated(api):
            config = api.configuration()
            self.short_url_length = config[u'short_url_length']
            self.short_url_length_https = config[u'short_url_length_https']

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
            responses = []
            tweets = self.compose_tweets(status)
            # print tweets
            for tweet in tweets:
                responses.append(api.update_status(status=tweet))
            base_url = 'https://twitter.com/'
            for response in responses:
                user = response.user
                name = user.name
                tweet_id = response.id_str
                yield '{}{}/status/{}'.format(base_url, name, tweet_id)

    def compose_tweets(self, message):
        words = message.split(' ')
        tweets = []
        current = ''
        running_total = 0
        for index in range(len(words)):
            word = words[index].strip()
            if is_url(word):
                current += word[1:-1]
            else:
                current += word
            running_total += self.get_length_for_word(word)
            # print '[{}] "{}"'.format(running_total, current.encode('utf-8'))
            if index + 1 < len(words):
                next_word = words[index+1].strip()
            current += ' '
            running_total += 1
            if next_word:
                if running_total + self.get_length_for_word(next_word) > 130:
                    tweets.append(current)
                    current = ''
                    running_total = 0
            else:
                tweets.append(current)
                break
        if len(tweets) > 1:
            for index in range(len(tweets)):
                tweets[index] += '({}/{})'.format(index+1, len(tweets))
        return tweets

    def get_length_for_word(self, word):
        if is_url(word):
            return self.short_url_length
        return len(word)


def is_url(word):
    """Currently does not work"""
    regex = re.compile(ur'^<https?:\/\/.+\|?.*>', re.UNICODE)
    match = regex.match(word)
    if match:
        return True
    return False
