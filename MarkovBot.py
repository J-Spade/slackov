import slackbot
import time
import random
import pickle
import json


class MarkovBot(slackbot.Slackbot):
        

	talkBackFreq = 1
	isLearning = True
	censorWords = True

	STOPWORD = 'BOGON'
        
	#		key	       come-befores       come-afters
	dictionary = { STOPWORD : ( [ (STOPWORD, 1) ], [ (STOPWORD, 1) ] ) }

	def __init__(self, token, client, id):

		slackbot.Slackbot.__init__(self, token, client, id)
		
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

            	while (True):
			
			try:
                    		next = words[index + 1]

			except IndexError:
		      		# this means we got to the end of the sentence
		      		break
                
			# add 'next' as a word that comes after 'word'
                	if self.dictionary.has_key(word):

				temp = self.dictionary.get(word)[1]
				wordindex = self.wordIndexInList(next, temp)
				
				if (wordindex == -1):
					temp.append( (next, 1) )
				else:
					prevcount = temp[wordindex][1]
					temp[wordindex] = (next, prevcount + 1)
					
                	else:
                    		self.dictionary[word] = ( [], [(next, 1)] )
                    
			# add 'word' as a word that comes before 'next'
			if self.dictionary.has_key(next):
				
				othertemp = self.dictionary.get(next)[0]
				wordindex = self.wordIndexInList(word, othertemp)

				if (wordindex == -1):
					othertemp.append( (word, 1) )
				else:
					prevcount = othertemp[wordindex][1]
					othertemp[wordindex] = (word, prevcount + 1)

                	else:
                    		self.dictionary[next] = ( [(word, 1)], [] )

			
                	index  = index + 1
			word = words[index]
		
			# print self.dictionary
        

	def generateChain(self, message):
        	
		words = message.split()
		
		# remove words we don't know
		for checkword in words:

			if not (self.dictionary.has_key(checkword)):
				words.remove(checkword)

		if len(words) == 0:
			return ''

		seed = random.choice(words)

		chain = ''	
		

		# forwards
		word = seed
            	while (word != self.STOPWORD) and (self.dictionary.has_key(word)):
			
			space = ('' if chain == '' else ' ')
               		chain = chain + space + word
               		word = self.chooseWordFromList( self.dictionary.get(word)[1] )
          

		# backwards
		if self.dictionary.has_key(word):
			word = self.chooseWordFromList( self.dictionary.get(seed)[0] )
			# so we don't have the seed twice


		while (word != self.STOPWORD) and (self.dictionary.has_key(word)):
               		chain = word + ' ' + chain
               		word = self.chooseWordFromList( self.dictionary.get(word)[0] )

		return chain
            
        

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

		rand = random.randint(1, sum)

		for index in range( len(stops) ):
			
			if (rand <= stops[index]):
				return list[index - 1][0]
			
		return list[0][0]




