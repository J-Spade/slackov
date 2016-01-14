import slackbot
from twitbot import TwitterBot
import time
import random
import pickle
import json
import string


class MarkovBot(slackbot.Slackbot):

    talkBackFreq = 0.05
    isLearning = True
    censorWords = True #not implemented
    lastMessages = {}

    STOPWORD = 'BOGON'

    #       key        come-befores       come-afters
    dictionary = { STOPWORD : ( [ (STOPWORD, 1) ], [ (STOPWORD, 1) ] ) }

    def __init__(self, client, slack, twitter):
        token = slack['token']
        user_id = slack['id']
        avatarsource = slack['avatarsource']

        slackbot.Slackbot.__init__(self, token, client, user_id, avatarsource)

        consumer_key = twitter['consumer_key']
        consumer_secret = twitter['consumer_secret']
        access_token = twitter['access_token']
        access_token_secret = twitter['access_token_secret']

        self.twitter = TwitterBot(consumer_key, consumer_secret, access_token, access_token_secret)

        try:
            self.loadDictionary()
            print ('DICTIONARY LOADED SUCCESSFULLY')
        except IOError:
            print ('DICTIONARY COULD NOT BE LOADED')



    def onMessageReceived(self, target, sender, message):
        callargs = {'token': self.TOKEN, 'user': sender}
        info = self.CLIENT.api_call('users.info', callargs)
        sentByAdmin = json.loads(info)['user']['is_admin']

        if self.doCommands(target, sender, message, sentByAdmin):
            return

        if sender != 'USLACKBOT':
            message = message.lower()
            if self.isLearning:
                lines = message.split('\n')
                for line in lines:
                    for sentence in line.split('. '):
                        if sentence.endswith('.'):  # get rid of last .
                            sentence = sentence[:-1]
                        self.interpretMessage(sentence)
            if random.random() < self.talkBackFreq:
                response = self.generateChain(message)
                if response != '':
                    self.sendMessage(target, response)

    def onMyMessageReceived(self, channel, message, timestamp):
        if timestamp not in self.lastMessages:
            self.lastMessages[timestamp] = message

    def onPrivateMessageReceived (self, channel, sender, message):
        # PMs don't teach the bot anything, but will always get a response (if the bot can provide one)

        callargs = {'token': self.TOKEN, 'user': sender}
        info = self.CLIENT.api_call('users.info', callargs)
        sentByAdmin = json.loads(info)['user']['is_admin']

        if self.doCommands(channel, sender, message, sentByAdmin):
            return

        message = message.lower()

        response = self.generateChain(message)
        if response != '':
            self.sendMessage(channel, response)

    def onReactionReceived (self, channel, timestamp):
        if self.twitter.isActivated():
            if timestamp in self.lastMessages:
                message = self.lastMessages[timestamp]
                self.twitter.post(message)


    def doCommands(self, target, sender, message, sentByAdmin):
        if sentByAdmin and ('!saveDict' in message):
            try:
                self.saveDictionary()
                self.sendMessage(target, 'DICTIONARY SAVED SUCCESSFULLY')
            except IOError:
                self.sendMessage(target, 'DICTIONARY COULD NOT BE SAVED')
            return True
        elif sentByAdmin and ('!loadDict' in message):
            try:
                self.loadDictionary()
                self.sendMessage(target, 'DICTIONARY LOADED SUCCESSFULLY')
            except IOError:
                self.sendMessage(target, 'DICTIONARY COULD NOT BE LOADED')
            return True
        elif sentByAdmin and ('!eraseDict' in message):

            self.dictionary = {
                self.STOPWORD : ([self.STOPWORD], [self.STOPWORD])
            }
            self.sendMessage(target, 'DICTIONARY ERASED (NOT SAVED YET)')
            return True
        elif sentByAdmin and ('!learn' in message):
            self.toggleLearn()
            self.sendMessage(target, 'I AM {} LEARNING'.format('NOW' if self.isLearning else 'NO LONGER'))
            return True
        elif '!search' in message:
            try:
                message = message.lower()
                searchterms = message.split()[1:]

                if len(searchterms) == 1:
                    phrases = []
                    for key in self.dictionary:
                        if searchterms[0] == key.split()[0] or (len(key.split()) > 1 and searchterms[0] == key.split()[1]):
                            phrases.append(key)
                    self.sendMessage(target, '"%s" in pairs: %s' % (searchterms[0], str(phrases)))
                else:
                    key = searchterms[0] + ' ' + searchterms[1]
                    if self.dictionary.has_key(key):
                        self.sendMessage(target, '"%s": %s' % (key, str(self.dictionary.get(key))))
                    else:
                        self.sendMessage(target, '"%s" not found in dictionary' % key)
            except IndexError:
                self.sendMessage(target, 'MALFORMED COMMAND')
            return True
        elif '!talkback' in message:
            try:
                self.talkBackFreq = float(message.split()[1])
                self.sendMessage(target, ('RESPONDING PROBABILITY SET TO %3f' % self.talkBackFreq))
            except IndexError:
                self.sendMessage(target, 'MALFORMED COMMAND')
            return True
        elif sentByAdmin and ('!quit' in message):
            self.quit()
            return True
        elif '!avatar' in message:
            self.sendMessage(target, 'SOURCE OF MY CURRENT AVATAR: %s' % self.AVATARSOURCE)
            return True

        #elif ('!nowplaying' in message):
        #   songname, songartist = self.generateSong()
        #   self.sendMessage(target, 'Now Playing: "%s", by %s' % (songname, songartist))
        #   return True

        return False # did not find a command

    def onQuit(self):
        # try:
        #   self.saveDictionary()
        #   print ('DICTIONARY SAVED SUCCESSFULLY')
        # except IOError:
        #   print ('DICTIONARY COULD NOT BE SAVED')
        pass

    def interpretMessage(self, message):
        words = message.split()
        words.append(self.STOPWORD)
        words.insert(0, self.STOPWORD)

        index = 0
        word = words[index]
        # cannot be out of range; at least (stop, stop, word, stop, stop)
        wordpair = words[index] + ' ' + words[index + 1]

        while True:
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

        if '<{}>'.format(self.users[self.BOT_ID]) in words[1]:
            del words[1]

        if len(words) < 2:
            return ''

        # remove stuff we don't know
        wordpair = ''
        index = 0
        seedcandidates = []
        while index < len(words) - 1:
            wordpair = words[index] + ' ' + words[index + 1]
            if self.dictionary.has_key(wordpair):
                seedcandidates.append(wordpair)
            index = index + 1
        if len(seedcandidates) == 0:
            return ''

        chain = ''

        seed = random.choice(seedcandidates)

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




