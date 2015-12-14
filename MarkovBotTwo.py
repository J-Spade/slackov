import slackbot
import time
import random
import pickle
import json
import string


class MarkovBot(slackbot.Slackbot):
        

	talkBackFreq = 0.05
	isLearning = True
	censorWords = True #not implemented
	
	STOPWORD = 'BOGON'
        
	#		key	       come-befores       come-afters
	dictionary = { STOPWORD : ( [ (STOPWORD, 1) ], [ (STOPWORD, 1) ] ) }

	def __init__(self, token, client, id, avatarsource):

		slackbot.Slackbot.__init__(self, token, client, id, avatarsource)
		
		try:
			self.loadDictionary()
			print ('DICTIONARY LOADED SUCCESSFULLY')
		except IOError:
			print ('DICTIONARY COULD NOT BE LOADED')



	def onMessageReceived(self, target, sender, message):	

		callargs = {'token': self.TOKEN, 'user': sender}
		info = self.CLIENT.api_call('users.info', callargs)
		sentByAdmin = json.loads(info)['user']['is_admin']


		# command handling
		if sentByAdmin and ('!saveDict' in message):
			
			try:
				self.saveDictionary()
				self.sendMessage(target, 'DICTIONARY SAVED SUCCESSFULLY')
			except IOError:
				self.sendMessage(target, 'DICTIONARY COULD NOT BE SAVED')
			return
                
		elif sentByAdmin and ('!loadDict' in message):
			
			try:
				self.loadDictionary()
				self.sendMessage(target, 'DICTIONARY LOADED SUCCESSFULLY')
			except IOError:
				self.sendMessage(target, 'DICTIONARY COULD NOT BE LOADED')
			return		

		elif sentByAdmin and ('!eraseDict' in message):

			self.dictionary = { self.STOPWORD : ([self.STOPWORD], [self.STOPWORD]) }
			self.sendMessage(target, 'DICTIONARY ERASED (NOT SAVED YET)')
		
		elif sentByAdmin and ('!learn' in message):
			self.toggleLearn()
			self.sendMessage(target, 'I AM ' + ('NOW' if self.isLearning else 'NO LONGER') + ' LEARNING')
			return 

		elif sentByAdmin and ('!talkback' in message):
			try:
				self.talkBackFreq = float(message.split()[1])
				self.sendMessage(target, ('RESPONDING PROBABILITY SET TO %3f' % self.talkBackFreq))
			except IndexError:
				self.sendMessage(target, 'MALFORMED COMMAND')

		elif sentByAdmin and ('!quit' in message):
			self.quit()

		elif ('!avatar' in message):
			self.sendMessage(target, 'SOURCE OF MY CURRENT AVATAR: %s' % self.AVATARSOURCE)

		#elif ('!nowplaying' in message):
		#	songname, songartist = self.generateSong()
		#	self.sendMessage(target, 'Now Playing: "%s", by %s' % (songname, songartist))


#	#	# all other messages handled here
		elif sender != 'USLACKBOT':
			
			message = message.lower()

			if self.isLearning:

				sentences = message.split('. ')
				for sentence in sentences:
					if sentence.endswith('.'):	# get rid of last .
						sentence = sentence[:-1]
					self.interpretMessage(sentence)
                    

             		if random.random() < self.talkBackFreq:

                    		response = self.generateChain(message)

				if response != '':
                    			self.sendMessage(target, response)
                
        
	def onPrivateMessageReceived (self, channel, sender, message):

		# PMs don't teach the bot anything, but will always get a response (if the bot can provide one)
		
		message = message.lower()

		response = self.generateChain(message)
		if response != '':
			self.sendMessage(channel, response)




	def onQuit(self):

		# try:
		# 	self.saveDictionary()
		# 	print ('DICTIONARY SAVED SUCCESSFULLY')
		# except IOError:
		# 	print ('DICTIONARY COULD NOT BE SAVED')
		pass

	def interpretMessage(self, message):

            	words = message.split()
            	words.append(self.STOPWORD)
		words.insert(0, self.STOPWORD)
            
            	index = 0
		word = words[index]
            	wordpair = words[index] + ' ' + words[index + 1] # cannot be out of range; at least (stop, stop, word, stop, stop)

            	while (True):
			
			try:
                    		next = words[index + 2]
				nextpair = words[index + 1] + ' ' + words[index + 2]

			except IndexError:
		      		# this means we got to the end of the sentence
		      		break
                
			# add 'next' as a word that comes after 'wordpair'
                	if self.dictionary.has_key(wordpair):

				temp = self.dictionary.get(wordpair)[1]
				wordindex = self.wordIndexInList(next, temp)
				
				if (wordindex == -1):
					temp.append( (next, 1) )
				else:
					prevcount = temp[wordindex][1]
					temp[wordindex] = (next, prevcount + 1)
					
                	else:
                    		self.dictionary[wordpair] = ( [], [(next, 1)] )
                    
			# add 'word' as a word that comes before 'nextpair'
			if self.dictionary.has_key(nextpair):
				
				othertemp = self.dictionary.get(nextpair)[0]
				wordindex = self.wordIndexInList(word, othertemp)

				if (wordindex == -1):
					othertemp.append( (word, 1) )
				else:
					prevcount = othertemp[wordindex][1]
					othertemp[wordindex] = (word, prevcount + 1)

                	else:
                    		self.dictionary[nextpair] = ( [(word, 1)], [] )

			
                	index = index + 1
			word = words[index]
			wordpair = word + ' ' + words[index + 1]
		
		#print self.dictionary
        

	def generateChain(self, message):
        	
		words = message.split()
		words.append(self.STOPWORD)
		words.insert(0, self.STOPWORD)

		if len(words) < 2:
			return ''
		
		# remove words we don't know
		#for checkword in words:
		#
		#	if not (self.dictionary.has_key(checkword)):
		#		words.remove(checkword)


		#if len(words) == 0:
		#	return ''

		# see if we can use a word that has more than two or three letters
		#longwords = list(words)

		#for word in longwords:
		#	if len(word) <= 3:
		#		longwords.remove(word)

		#if len(longwords) > 0:
		#	seed = random.choice(longwords)
		#else:
		#	seed = random.choice(words)

		chain = ''	
		
		seedindex = random.randint(0, len(words) - 2)
		seed = words[seedindex] + ' ' + words[seedindex + 1]

		# forwards
		wordpair = seed
		if (self.dictionary.has_key(wordpair)):
			chain = wordpair
		#print wordpair
            	while (wordpair.split()[1] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
               		wordpair = wordpair.split()[1] + ' ' + self.chooseWordFromList( self.dictionary.get(wordpair)[1] )
			#print wordpair
               		chain = chain + ' ' + wordpair.split()[1]

		# backwards
		wordpair = seed
		if self.dictionary.has_key(wordpair) and wordpair.split()[0] != self.STOPWORD:
			wordpair = self.chooseWordFromList( self.dictionary.get(wordpair)[0] ) + ' ' + wordpair.split()[0]
		# so we don't have the seed twice


		while (wordpair.split()[0] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
			#print wordpair
               		chain = wordpair.split()[0] + ' ' + chain
               		wordpair = self.chooseWordFromList( self.dictionary.get(wordpair)[0] ) + ' ' + wordpair.split()[0]

		return chain.replace(self.STOPWORD, '')
            

	def saveDictionary(self):
        
            	output = open('Markov_Dict.pkl', 'w')
            	pickle.dump(self.dictionary, output)
            	output.close()
        

	def loadDictionary(self):
        
		input = open('Markov_Dict.pkl', 'r')
		self.dictionary = pickle.load(input)
		input.close()


	def toggleLearn(self):

		self.isLearning = not self.isLearning


	def wordIndexInList(self, findword, list):

		word = ''
		for index in range( len(list) ):
			if (list[index][0] == findword):
				return index
		return -1



	def chooseWordFromList(self, list):
		sum = 0
		stops = [0]

		for pair in list:

			sum = sum + pair[1]
			stops.append(sum)

		if sum > 1:
			rand = random.randint(1, sum)
		else:
			rand = 1

		for index in range( len(stops) ):
			
			if (rand <= stops[index]):
				return list[index - 1][0]
			
		return list[0][0]




