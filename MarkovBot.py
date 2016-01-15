"""Imports"""
import random
import pickle
import json
import slackbot

from twitbot import TwitterBot

class MarkovBot(slackbot.Slackbot):
    """Handles chain generation and bot behavior"""

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
            self.load_dictionary()
            print 'DICTIONARY LOADED SUCCESSFULLY'
        except IOError:
            print 'DICTIONARY COULD NOT BE LOADED'

    def on_message_received(self, target, sender, message):
        callargs = {'token': self.TOKEN, 'user': sender}
        info = self.CLIENT.api_call('users.info', callargs)
        sentByAdmin = json.loads(info)['user']['is_admin']

        if self.do_commands(target, sender, message, sentByAdmin):
            return

        if sender != 'USLACKBOT':
            message = message.lower()
            if self.isLearning:
                lines = message.split('\n')
                for line in lines:
                    for sentence in line.split('. '):
                        if sentence.endswith('.'):  # get rid of last .
                            sentence = sentence[:-1]
                        self.interpret_message(sentence)
            if random.random() < self.talkBackFreq:
                response = self.generate_chain(message)
                if response != '':
                    self.send_message(target, response)

    def on_my_message_received(self, timestamp, message):
        print 'my message!'
        if timestamp not in self.lastMessages:
            self.lastMessages[timestamp] = message
            print self.lastMessages

    def on_private_message_received(self, channel, sender, message):
        """
        PMs don't teach the bot anything,
        but will always get a response (if the bot can provide one)
        """

        callargs = {'token': self.TOKEN, 'user': sender}
        info = self.CLIENT.api_call('users.info', callargs)
        sentByAdmin = json.loads(info)['user']['is_admin']

        if self.do_commands(channel, sender, message, sentByAdmin):
            return

        message = message.lower()

        response = self.generate_chain(message)
        if response != '':
            self.send_message(channel, response)

    def on_reaction_received(self, channel, timestamp):
        if timestamp in self.lastMessages:
            message = self.lastMessages[timestamp]
            print message
            self.twitter.post(message)
            del self.lastMessages[timestamp]

    def do_commands(self, target, sender, message, sentByAdmin):
        if sentByAdmin and ('!saveDict' in message):
            try:
                self.save_dictionary()
                self.send_message(target, 'DICTIONARY SAVED SUCCESSFULLY')
            except IOError:
                self.send_message(target, 'DICTIONARY COULD NOT BE SAVED')
            return True
        elif sentByAdmin and ('!loadDict' in message):
            try:
                self.load_dictionary()
                self.send_message(target, 'DICTIONARY LOADED SUCCESSFULLY')
            except IOError:
                self.send_message(target, 'DICTIONARY COULD NOT BE LOADED')
            return True
        elif sentByAdmin and ('!eraseDict' in message):

            self.dictionary = {
                self.STOPWORD : ([self.STOPWORD], [self.STOPWORD])
            }
            self.send_message(target, 'DICTIONARY ERASED (NOT SAVED YET)')
            return True
        elif sentByAdmin and ('!learn' in message):
            self.toggle_learn()
            print_message = 'I AM {} LEARNING'
            self.send_message(target,
                              print_message.format('NOW' if self.isLearning else 'NO LONGER'))
            return True
        elif '!search' in message:
            try:
                message = message.lower()
                searchterms = message.split()[1:]

                if len(searchterms) == 1:
                    phrases = []
                    for key in self.dictionary:
                        if searchterms[0] == key.split()[0] or \
                                             (len(key.split()) > 1 and \
                                             searchterms[0] == key.split()[1]):
                            phrases.append(key)
                    self.send_message(target, '"%s" in pairs: %s' % (searchterms[0], str(phrases)))
                else:
                    key = searchterms[0] + ' ' + searchterms[1]
                    if self.dictionary.has_key(key):
                        self.send_message(target, '"%s": %s' % (key, str(self.dictionary.get(key))))
                    else:
                        self.send_message(target, '"%s" not found in dictionary' % key)
            except IndexError:
                self.send_message(target, 'MALFORMED COMMAND')
            return True
        elif '!talkback' in message:
            try:
                self.talkBackFreq = float(message.split()[1])
                self.send_message(target, ('RESPONDING PROBABILITY SET TO %3f' % self.talkBackFreq))
            except (IndexError, TypeError):
                self.send_message(target, 'MALFORMED COMMAND')
            return True
        elif sentByAdmin and ('!quit' in message):
            self.quit()
            return True
        elif '!avatar' in message:
            self.send_message(target, 'SOURCE OF MY CURRENT AVATAR: %s' % self.AVATARSOURCE)
            return True

        #elif ('!nowplaying' in message):
        #   songname, songartist = self.generateSong()
        #   self.sendMessage(target, 'Now Playing: "%s", by %s' % (songname, songartist))
        #   return True

        return False # did not find a command

    def on_quit(self):
        # try:
        #   self.saveDictionary()
        #   print ('DICTIONARY SAVED SUCCESSFULLY')
        # except IOError:
        #   print ('DICTIONARY COULD NOT BE SAVED')
        pass

    def interpret_message(self, message):
        """Interprets a message"""
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
                wordindex = self.word_index_in_list(next, temp)
                if wordindex == -1:
                    temp.append((next, 1))
                else:
                    prevcount = temp[wordindex][1]
                    temp[wordindex] = (next, prevcount + 1)
            else:
                self.dictionary[wordpair] = ([], [(next, 1)])

            # add 'word' as a word that comes before 'nextpair'
            if self.dictionary.has_key(nextpair):
                othertemp = self.dictionary.get(nextpair)[0]
                wordindex = self.word_index_in_list(word, othertemp)
                if wordindex == -1:
                    othertemp.append((word, 1))
                else:
                    prevcount = othertemp[wordindex][1]
                    othertemp[wordindex] = (word, prevcount + 1)

            else:
                self.dictionary[nextpair] = ([(word, 1)], [])

            index = index + 1
            word = words[index]
            wordpair = word + ' ' + words[index + 1]

        #print self.dictionary


    def generate_chain(self, message):
        """Generates a Markov chain from a message"""
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
        if self.dictionary.has_key(wordpair):
            chain = wordpair
        #print wordpair
        while (wordpair.split()[1] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
            wordpair = wordpair.split()[1] + ' ' + \
                        self.choose_word_from_list(self.dictionary.get(wordpair)[1])
            #print wordpair
            chain = chain + ' ' + wordpair.split()[1]

        # backwards
        wordpair = seed
        if self.dictionary.has_key(wordpair) and wordpair.split()[0] != self.STOPWORD:
            wordpair = self.choose_word_from_list(
                self.dictionary.get(wordpair)[0]) + \
                ' ' + wordpair.split()[0]
        # so we don't have the seed twice


        while (wordpair.split()[0] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
            #print wordpair
            chain = wordpair.split()[0] + ' ' + chain
            wordpair = self.choose_word_from_list(
                self.dictionary.get(wordpair)[0]) + \
                ' ' + wordpair.split()[0]

        return chain.replace(self.STOPWORD, '')


    def save_dictionary(self):
        """Save the dictionary to disk"""
        output = open('Markov_Dict.pkl', 'w')
        pickle.dump(self.dictionary, output)
        output.close()


    def load_dictionary(self):
        """Load the dictionary file"""
        input = open('Markov_Dict.pkl', 'r')
        self.dictionary = pickle.load(input)
        input.close()


    def toggle_learn(self):
        """Toggles the learning state"""
        self.isLearning = not self.isLearning


    def word_index_in_list(self, findword, list):
        """Get the index of a word in a list"""
        word = ''
        for index in range( len(list) ):
            if list[index][0] == findword:
                return index
        return -1



    def choose_word_from_list(self, list):
        """Pick a random word from a list"""
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
            if rand <= stops[index]:
                return list[index - 1][0]

        return list[0][0]




