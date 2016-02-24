"""Imports"""
import time
import datetime
import threading
import Queue
import json

from slackclient import SlackClient


# daemon thread; runs while the bot is running
# places lines from the server into the input queue
class _inputThread(threading.Thread):

    def __init__(self, client, queue):
        threading.Thread.__init__(self)
        self.client = client
        self.inputqueue = queue
	self.daemon = True

    def run(self):
        while 1:
            messages = self.client.rtm_read()
            for message in messages:
                self.inputqueue.put(message)
            time.sleep(1)

    def stop(self):
        """Stops the input thread from running"""
        self._Thread__stop()


# takes lines from the input queue, and processes them
class _processThread(threading.Thread):

    keepgoing = True

    def __init__(self, client, bot, channelids, users):
        threading.Thread.__init__(self)
        self.client = client
        self.bot = bot
        self.channelids = channelids
        self.users = users

    def stop(self):
        """Stops the process thread from running"""
        self.keepgoing = False
        self._Thread__stop()

    def run(self):
        self.keepgoing = True

        while self.keepgoing:
            message = self.bot._inputqueue.get(True)

            if u'ok' in message:
                self.process_my_message(message)
            elif u'type' in message:
                if message[u'type'] == 'message':
                    if u'subtype' in message:
                        if message[u'subtype'] == 'channel_join':
                            self.process_channel_join(message)
                    else:
                        self.process_message(message)
                elif message[u'type'] == 'reaction_added':
                    self.process_reaction(message)

    def process_message(self, message):
        """Handles processing for normal messages"""
        sender = message[u'user']
        channel = message[u'channel']
        text = message[u'text'].encode('utf-8')
	currtime = message[u'ts']

        for user_id in self.users:
            text = text.replace(user_id, self.users[user_id])

        print '::#{} [{}] <{}> {}'.format(channel, currtime, self.users[sender], text)

        if channel not in self.channelids:
            self.bot.on_private_message_received(channel, sender, text)
        elif '<@{}>'.format(self.users[self.bot.BOT_ID]) in text:
	    if '<@{}>'.format(self.users[self.bot.BOT_ID]) in text.split()[0]:
		if len(text.split(' ', 1)) > 1:
			text = text.split(' ', 1)[1]
            		self.bot.on_private_message_received(channel, sender, text)
		else:
			self.bot.on_name_ping_received(channel, sender)
        else:
            self.bot.on_message_received(channel, sender, text)

    def process_my_message(self, message):
        """Handles processing for bot messages"""
        if message[u'ok']:
            timestamp = message[u'ts']
            text = message[u'text']
            self.bot.on_my_message_received(timestamp, text)

    def process_reaction(self, message):
        """Handles processing for reactions (namely twitter reactions)"""
        if message[u'reaction'] == 'twitter':
            sender = message[u'user']
            item = message[u'item']
	    currtime = message[u'event_ts']
            channel = item[u'channel']
            timestamp = item[u'ts']

            print_message = '::#{} [{}] <{}> requested a tweet for "{}"'
            print print_message.format(channel, currtime, self.users[sender], timestamp)
            self.bot.on_reaction_received(channel, timestamp)

    def process_channel_join(self, message):
        """Handles processing for channel joins"""
        user_id = message[u'user']
        callargs = {'token': self.bot.TOKEN, 'user': user_id}
        info = self.client.api_call('users.info', callargs)
        name = json.loads(info)['user']['name']
        self.bot.users[user_id] = name
	currtime = message[u'ts']
        print '::[{}] <{}> ((JOINED THE CHANNEL))'.format(currtime, name)

# sends lines from the output queue to the server
class _outputThread(threading.Thread):

    def __init__(self, client, queue):
        threading.Thread.__init__(self)
        self.client = client
        self.outputqueue = queue
	self.daemon = True

    def run(self):
        while 1:
            message = self.outputqueue.get(True)
            self.client.rtm_send_message(message[u'channel'], message[u'text'])
            print '>> %s' % message[u'text']
            time.sleep(1)

    def stop(self):
        """Stops the output thread from running"""
        self._Thread__stop()

class Slackbot:

    inp = None
    process = None
    out = None

    def __init__(self, token, client, bot_id, avatarsource):

        self.TOKEN = token
        self.BOT_ID = bot_id
        self.AVATARSOURCE = avatarsource
        self.CLIENT = client
        self._inputqueue = Queue.Queue(50)
        self._outputqueue = Queue.Queue(50)

        self.users = {'USLACKBOT': 'slackbot'}
        self.channelids = []

    def start(self):
        """Starts the bot"""
        self.CLIENT = SlackClient(self.TOKEN)
        print self.CLIENT
        print 'CONNECTING...'

        if self.CLIENT.rtm_connect():
            print 'CONNECTED.'

            channels = json.loads(self.CLIENT.api_call('channels.list', {}))['channels']
            for chan in channels:
                self.channelids.append(chan['id'])
            privchannels = json.loads(self.CLIENT.api_call('groups.list', {}))['groups']
            for chan in privchannels:
                self.channelids.append(chan['id'])
            print 'CHANNELS: %s' % self.channelids

            userlist = json.loads(self.CLIENT.api_call('users.list', {}))['members']
            for user in userlist:
                self.users[user['id'].encode('utf-8')] = user['name'].encode('utf-8')
            print 'USERS: %s' % self.users

            self.inp = _inputThread(self.CLIENT, self._inputqueue)
            self.process = _processThread(self.CLIENT, self, self.channelids, self.users)
            self.out = _outputThread(self.CLIENT, self._outputqueue)
            self.inp.start()
            self.process.start()
            self.out.start()
        else:
            print "CONNECTION FAILED"


#   # functionality
    def quit(self):
        """Quits the bot"""
        self.process.stop()
	## daemon threads should not need this
        # self.inp.stop()
        # self.out.stop()
        self.on_quit()

    def send_message(self, channel, text):
        """Sends a message to the output queue"""
        self._outputqueue.put({u'channel': channel, u'text': text})

#   # event handling done by subclass

    def on_message_received(self, channel, sender, message):
        """
        Abstract method to handle received messages.

        This function must be overridden by a class that inherits Slackbot.
        """
        pass

    def on_name_ping_received(self, channel, sender):
        """
        Abstract method to handle received messages.

        This function must be overridden by a class that inherits Slackbot.
        """
        pass

    def on_my_message_received(self, timestamp, message):
        """
        Abstract method to handle bot messages.

        This function must be overridden by a class that inherits Slackbot.
        """
        pass

    def on_private_message_received(self, channel, sender, message):
        """
        Abstract method to handle received private messages.

        This function must be overridden by a class that inherits Slackbot.
        """
        pass

    def on_reaction_received(self, channel, message):
        """
        Abstract method to handle received reactions.

        This function must be overridden by a class that inherits Slackbot.
        """
        pass

    def on_quit(self):
        """
        Abstract method to handle quitting the bot.

        This function must be overridden by a class that inherits Slackbot.
        """
        pass
