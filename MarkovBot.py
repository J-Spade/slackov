"""Imports"""
import random
try:
   import cPickle as pickle
except:
   import pickle
import copy
import json
import slackbot
import string
import os
import threading
import time
import math

from twitbot import TwitterBot, clean_url

class MarkovBot(slackbot.Slackbot):
    """Handles chain generation and bot behavior"""

    talkBackFreq = 0.05
    isLearning = True
    censorWords = True #not implemented
    lastMessages = {}

    STOPWORD = 'BOGON'

    #       key        come-befores       come-afters
    DEFAULT_DICTIONARY = {STOPWORD: ([(STOPWORD, 1)], [(STOPWORD, 1)])}
    dictionary = copy.deepcopy(DEFAULT_DICTIONARY)

    wordcounts = {STOPWORD: 0}
    paircounts = {STOPWORD: 0}
    sentences_ever = 0

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

	self.dictLock = threading.Lock()

	print 'LOADING DICTIONARY...'
        try:
            self.load_dictionary()

            print 'COUNTING WORDS...'            
            for wordpair in self.dictionary:

                temp = wordpair.split()
                uses = 0
                for temp in self.dictionary.get(wordpair)[0]:
                    uses = uses + temp[1]
                self.paircounts[wordpair] = uses

                tally = 0
                for prev in self.dictionary.get(wordpair)[0]:
                    tally += prev[1]

                first = wordpair.split()[0]
                if not (self.wordcounts.has_key(first)):
                    self.wordcounts[first] = 0
                self.wordcounts[first] = self.wordcounts.get(first) + tally

                if wordpair != self.STOPWORD:
                    second = wordpair.split()[1]
                    if not (self.wordcounts.has_key(second)):
                        self.wordcounts[second] = 0
                    self.wordcounts[second] = self.wordcounts.get(second) + tally

            self.sentences_ever = self.wordcounts.get(self.STOPWORD)

            print 'STARTING AUTOSAVER...'
	    self.autosaver = _autoSaveThread(self)
	    self.autosaver.start()
        except IOError:
            print 'DICTIONARY COULD NOT BE LOADED'

    def on_message_received(self, target, sender, message):
        callargs = {'token': self.TOKEN, 'user': sender}
        info = self.CLIENT.api_call('users.info', token=self.TOKEN, user=sender)
        sentByAdmin = info['user']['is_admin']

        if self.do_commands(target, sender, message, sentByAdmin):
            return

        if sender != 'USLACKBOT':
            message = message.lower()
            if self.isLearning:
                lines = message.split(u'\n')
                for line in lines:
                    for sentence in line.split(u'. '):
                        if sentence.endswith(u'.'):  # get rid of last .
                            sentence = sentence[:-1]
                        self.interpret_message(sentence)
            if random.random() < self.talkBackFreq:
                response = self.generate_chain(message)
                if response != '':
                    self.send_message(target, response)

    def on_my_message_received(self, timestamp, message):
        if timestamp not in self.lastMessages:
            self.lastMessages[timestamp] = message

    def on_private_message_received(self, channel, sender, message):
        """
        PMs don't teach the bot anything,
        but will always get a response (if the bot can provide one)
        """
        callargs = {'token': self.TOKEN, 'user': sender}
        info = self.CLIENT.api_call('users.info', token=self.TOKEN, user=sender)
        sentByAdmin = info['user']['is_admin']

        if self.do_commands(channel, sender, message, sentByAdmin):
            return

        message = message.lower()

        response = self.generate_chain(message)
        if response != '':
            self.send_message(channel, response)

    def on_name_ping_received(self, channel, sender):
	self.send_message(channel, '<@%s>' % self.users[sender])

    def on_reaction_received(self, channel, timestamp):
        if timestamp in self.lastMessages:
            message = self.lastMessages[timestamp]
            links = self.twitter.post(message)
            del self.lastMessages[timestamp]
            if links:
                for link in links:
                    self.send_message(channel, link)

    def do_commands(self, target, sender, message, sentByAdmin):
        if sentByAdmin and ('!saveDict' in message):
            try:
                self.save_dictionary()
                self.send_message(target, 'DICTIONARY SAVED SUCCESSFULLY (%s bytes)' % str(os.path.getsize('Markov_Dict.pkl')))
            except IOError:
                self.send_message(target, 'DICTIONARY COULD NOT BE SAVED')
            return True
        elif sentByAdmin and ('!loadDict' in message):
            try:
                self.load_dictionary()
                self.send_message(target, 'DICTIONARY LOADED SUCCESSFULLY (%s bytes)' % str(os.path.getsize('Markov_Dict.pkl')))
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
        elif sentByAdmin and ('!cleanURL' in message):
            self.clean_urls_in_dictionary()
            self.send_message(target, 'LINKS IN DICTIONARY HAVE BEEN CLEANED')
            return True
        elif '!search' in message:
            try:
                message = message.lower()
                searchterms = message.split()[1:]
		for i in range(0, len(searchterms)):
		    searchterms[i] = clean_url(searchterms[i])
                if len(searchterms) == 1:
                    phrases = []
                    for key in self.dictionary:
                        if searchterms[0] == key.split()[0] or \
                                             (len(key.split()) > 1 and \
                                             searchterms[0] == key.split()[1]):
                            phrases.append(key)
                    self.send_message(target, u'"%s" in pairs: %s' % (searchterms[0], str(phrases)))
                else:
                    key = searchterms[0] + u' ' + searchterms[1]
                    if self.dictionary.has_key(key):
                        self.send_message(target, u'"%s": %s' % (key, str(self.dictionary.get(key))))
                    else:
                        self.send_message(target, u'"%s" not found in dictionary' % key)
            except IndexError:
                self.send_message(target, u'MALFORMED COMMAND')
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

        elif ('!nowplaying' in message):
           songname, songartist = self.generate_song()
           self.send_message(target, u'Now Playing: "%s", by %s' % (string.capwords(songname), string.capwords(songartist)))
           return True

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
	
	self.dictLock.acquire()
        words = message.split()
        words.append(self.STOPWORD)
        words.insert(0, self.STOPWORD)

        self.sentences_ever = self.sentences_ever + 1

        # find URLs, neaten them up
        for i in range(0, len(words)):
            words[i] = clean_url(words[i])

	for word in words:
            if !(self.wordcounts.has_key(word)):
                self.wordcounts[word] = 0
            self.wordcounts[word] = self.wordcounts.get(word) + 1

        index = 0
        word = words[index]
        # cannot be out of range; at least (stop, stop, word, stop, stop)
        wordpair = words[index] + u' ' + words[index + 1]

        while True:
            try:
                next = words[index + 2]
                nextpair = words[index + 1] + u' ' + words[index + 2]
            except IndexError:
                # this means we got to the end of the sentence
                break

            # add 'next' as a word that comes after 'wordpair'
            if self.dictionary.has_key(wordpair):
                temp = self.dictionary.get(wordpair)[1]
                wordindex = word_index_in_list(next, temp)
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
                wordindex = word_index_in_list(word, othertemp)
                if wordindex == -1:
                    othertemp.append((word, 1))
                else:
                    prevcount = othertemp[wordindex][1]
                    othertemp[wordindex] = (word, prevcount + 1)

            else:
                self.dictionary[nextpair] = ([(word, 1)], [])

            index = index + 1
            word = words[index]
            wordpair = word + u' ' + words[index + 1]

        #print self.dictionary
	self.dictLock.release()

    def generate_chain(self, message):
        """Generates a Markov chain from a message"""
        words = message.split()
        words.append(self.STOPWORD)
        words.insert(0, self.STOPWORD)

        # find URLs, neaten them up
        for i in range(0, len(words)):
            words[i] = clean_url(words[i])
        if '<{}>'.format(self.users[self.BOT_ID]) in words[1]:
            del words[1]

        if len(words) < 2:
            return ''


        # try to guess which word is the most important
        subject = self.STOPWORD
        confidence = 0

        for word in words:
            if self.wordcounts.has_key(word):
                tfidf = tf_idf(word, words, self.wordcounts, self.sentences_ever)
                if tfidf > confidence:
                    confidence = tfidf
                    subject = word

        # pick a word pair we've seen used with that word before as a seed
        pairs = []
        for wordpair in self.paircounts:
            temp = wordpair.split()
            if (temp[0] == subject) or ((len(temp) > 1) and (temp[1] == subject)):
                pairs.append((wordpair, self.paircounts.get(wordpair)))

        seed = choose_word_from_list(pairs)

        chain = ''

        # forwards
        wordpair = seed
        if self.dictionary.has_key(wordpair):
            chain = wordpair
        #print wordpair
        while (wordpair.split()[1] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
            wordpair = wordpair.split()[1] + u' ' + \
                        choose_word_from_list(self.dictionary.get(wordpair)[1])
            #print wordpair
            chain = chain + u' ' + wordpair.split()[1]

        # backwards
        wordpair = seed
        if self.dictionary.has_key(wordpair) and wordpair.split()[0] != self.STOPWORD:
            wordpair = choose_word_from_list(
                self.dictionary.get(wordpair)[0]) + \
                u' ' + wordpair.split()[0]
        # so we don't have the seed twice


        while (wordpair.split()[0] != self.STOPWORD) and (self.dictionary.has_key(wordpair)):
            #print wordpair
            chain = wordpair.split()[0] + u' ' + chain
            wordpair = choose_word_from_list(
                self.dictionary.get(wordpair)[0]) + \
                u' ' + wordpair.split()[0]

        return chain.replace(self.STOPWORD, u'')

    def generate_song(self):
	bandname = u''
	while True:
	    if bandname != u'':
		bandname = bandname + u' '
	    words = random.choice(self.dictionary.keys()).split()
	    index = random.randint(0, 1)
	    if words[index] == self.STOPWORD:
		bandname = bandname + words[1 - index]
	    else:
		bandname = bandname + words[index]
	    if random.random() > 0.6:
		break
	songtitle = u''
	seed = random.choice(self.dictionary.keys())
	firstword = seed.split()[0]
	secondword = seed.split()[1]
	if firstword != self.STOPWORD:
	    songtitle = firstword
	    currpair = seed
	    while True:
		end = False
		for prev in self.dictionary.get(currpair)[0]:
		    if prev[0] == self.STOPWORD:
			end = True
		if end:
		    break
		else:
		    prev = choose_word_from_list(self.dictionary.get(currpair)[0])
		    songtitle = prev + u' ' + songtitle
		    currpair = prev + u' ' + currpair.split()[0]
	if secondword != self.STOPWORD:
	    if songtitle == u'':
		songtitle = secondword
	    else:
		songtitle = songtitle + u' ' + secondword
	    currpair = seed
	    while True:
		end = False
		for next in self.dictionary.get(currpair)[1]:
		    if next[0] == self.STOPWORD:
			end = True
		if end:
		    break
		else:
		    next = choose_word_from_list(self.dictionary.get(currpair)[1])
		    songtitle = songtitle + u' ' + next
		    currpair = currpair.split()[1] + u' ' + next
	return songtitle, bandname

    def save_dictionary(self):
        """Save the dictionary to disk"""
	self.dictLock.acquire()
        output = open('Markov_Dict.pkl', 'w')
        pickle.dump(self.dictionary, output)
        output.close()
	self.dictLock.release()

    def load_dictionary(self):
        """Load the dictionary file"""
	self.dictLock.acquire()
        input = open('Markov_Dict.pkl', 'r')
        self.dictionary = pickle.load(input)
        input.close()
	self.dictLock.release()

    def toggle_learn(self):
        """Toggles the learning state"""
        self.isLearning = not self.isLearning

    def clean_urls_in_dictionary(self):
	self.dictLock.acquire()
        newdict = copy.deepcopy(self.DEFAULT_DICTIONARY)
        for key in self.dictionary:
            firsts = self.dictionary.get(key)[0]
            for i in range(0, len(firsts)):
                firsts[i] = (clean_url(firsts[i][0]), firsts[i][1])
            seconds = self.dictionary.get(key)[1]
            for i in range(0, len(seconds)):
                seconds[i] = (clean_url(seconds[i][0]), seconds[i][1])
	    newkey = clean_url(key.split()[0])
	    if len(key.split()) > 1:
		newkey = newkey + ' ' + clean_url(key.split()[1])
            newdict[newkey] = (firsts, seconds)
        self.dictionary = newdict
	self.dictLock.release()

class _autoSaveThread(threading.Thread):

    def __init__(self, bot):
	threading.Thread.__init__(self)
	self.bot = bot
	self.daemon = True

    def run(self):
	while (1):
	    time.sleep(3600)
	    try:
                self.bot.save_dictionary()
                print 'DICTIONARY AUTOSAVED SUCCESSFULLY (%s bytes)' % str(os.path.getsize('Markov_Dict.pkl'))
            except IOError:
                print 'COULD NOT AUTOSAVE DICTIONARY'

    def stop(self):
        self._Thread__stop()

def word_index_in_list(findword, word_list):
    """Get the index of a word in a list"""
    for index in range(len(word_list)):
        if word_list[index][0] == findword:
            return index
    return -1

def choose_word_from_list(word_list):
    """Pick a random word from a list"""
    total = 0
    stops = [0]
    for pair in word_list:
        total = total + pair[1]
        stops.append(total)
    if sum > 1:
        rand = random.randint(1, total)
    else:
        rand = 1
    for index in range(len(stops)):
        if rand <= stops[index]:
            return word_list[index - 1][0]
    return word_list[0][0]

def tf_idf(keyword, words, counts, totalcount):
    
    count = 0
    for word in words:
        if keyword == word:
            count = count + 1
    
    tf = float(count)/len(words)

    idf = math.log(float(totalcount) / counts.get(keyword))

    return tf*idf
