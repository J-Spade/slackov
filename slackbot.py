import time
import datetime
import threading
import Queue
import json

from slackclient import SlackClient

# daemon thread; runs while the bot is running
# places lines from the server into the input queue
class _inputThread(threading.Thread):

	def __init__ (self, client, queue):
		self.client = client
		self.inputqueue = queue
		threading.Thread.__init__(self)

	def run (self):
		while 1:
			messages = self.client.rtm_read()
			for message in messages:
				self.inputqueue.put(message)
			time.sleep(1)

	def stop (self):
		self._Thread__stop()


# takes lines from the input queue, and processes them
class _processThread(threading.Thread):

	keepgoing = True

	def __init__ (self, client, bot, channelids, users):
		self.client = client
		self.bot = bot
		self.channelids = channelids
		self.users = users
		threading.Thread.__init__ (self)

	def stop (self):
		self.keepgoing = False
		self._Thread__stop()

	def run (self):
		self.keepgoing = True

		while self.keepgoing:

			message = self.bot._inputqueue.get(True)
			currtime = str(datetime.datetime.now()).split(' ')[1].split('.')[0]

			if (u'type' in message):
				if (message[u'type'] == 'message'):
					if (u'subtype' in message):
						if (message[u'subtype'] == 'channel_join'):
							id = message[u'user']
							callargs = {'token': self.bot.TOKEN, 'user': id}
							info = self.client.api_call('users.info', callargs)
							name = json.loads(info)['user']['name']
							self.bot.users[id] = name
							print '::[%s] <%s> ((JOINED THE CHANNEL))' % (currtime, name)
					else:
						sender = message[u'user']
						channel = message[u'channel']
						text = message[u'text']
						
						for id in self.users:
							text = text.replace(str(id), str(self.users[id]))
			
						print '::#%s [%s] <%s> %s' % (channel, currtime, self.users[sender], text)
						if (channel not in self.channelids) or (('<@%s>' % self.users[self.bot.ID]) in text):
							self.bot.onPrivateMessageReceived(channel, sender, text)
						else:
							self.bot.onMessageReceived(channel, sender, text)
	

		

# sends lines from the output queue to the server
class _outputThread(threading.Thread):

	def __init__ (self, client, queue):
		self.client = client
		self.outputqueue = queue
		threading.Thread.__init__(self)

	def run (self):
		while 1:
			message = self.outputqueue.get(True)
			self.client.rtm_send_message(message[u'channel'], message[u'text'])
			print '>> %s' % message[u'text']
			time.sleep(1)

	def stop (self):
		self._Thread__stop()

class Slackbot:

	def __init__ (self, token, client, id, avatarsource):
		
		self.TOKEN = token
		self.ID = id
		self.AVATARSOURCE = avatarsource
		self.CLIENT = client
		self._inputqueue = Queue.Queue(50)
		self._outputqueue = Queue.Queue(50)

		self.users = {'USLACKBOT': 'slackbot'}
		self.channelids = []

	def start(self):

		self.CLIENT = SlackClient(self.TOKEN)
		print self.CLIENT
		print 'CONNECTING...'

		if self.CLIENT.rtm_connect():
			print 'CONNECTED.'
			
			channels = json.loads(self.CLIENT.api_call('channels.list', {}))['channels']	
			for chan in channels:
				self.channelids.append(chan['id'])
			
			print 'CHANNELS: %s' % self.channelids

			userlist = json.loads(self.CLIENT.api_call('users.list', {}))['members']
			for user in userlist:
				self.users[str(user['id'])] = str(user['name'])
			print 'USERS: %s' % self.users

			self.inp = _inputThread(self.CLIENT, self._inputqueue)
			self.process = _processThread(self.CLIENT, self, self.channelids, self.users)
			self.out = _outputThread(self.CLIENT, self._outputqueue)
			self.inp.start()
			self.process.start()
			self.out.start()
		else:
			print "Connection Failed."


#	# functionality


	def quit (self):
		self.process.stop()
		self.inp.stop()
		self.out.stop()
		self.onQuit()

	def sendMessage (self, channel, text):
		self._outputqueue.put({u'channel': channel, u'text': text})



#	# event handling done by subclass



	def onMessageReceived (self, channel, sender, message):
		
		# This function must be overridden by a class that inherits IRCbot.
		pass

	def onPrivateMessageReceived (self, channel, sender, message):

		# this function must be overriden by a class that inherits IRCbot.
		pass

	def onQuit(self):

		# this function should be overridden by the class that inherits this one
		pass
