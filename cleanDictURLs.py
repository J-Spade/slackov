"""
import pickle
import re

STOPWORD = 'BOGON'

input = open('Markov_Dict.pkl', 'r')
dictionary = pickle.load(input)
input.close()

keystochange = []

#       key        come-befores       come-afters
newdict = { STOPWORD : ( [ (STOPWORD, 1) ], [ (STOPWORD, 1) ] ) }

for key in dictionary:
	firsts = dictionary.get(key)[0]
	for i in range (0, len(firsts)):
		if re.match(r'^<https?:\/\/.+\|?.*>$', firsts[i][0]):
			firsts[i] = (firsts[i][0][1:-1], firsts[i][1])
			if '|' in firsts[i][0]:
				firsts[i] = (firsts[i][0].split('|')[1], firsts[i][1])
	seconds = dictionary.get(key)[1]
	for i in range (0, len(seconds)):
		if re.match(r'^<https?:\/\/.+\|?.*>$', seconds[i][0]):
			seconds[i] = (seconds[i][0][1:-1], seconds[i][1])
			if '|' in seconds[i][0]:
				seconds[i] = (seconds[i][0].split('|')[1], seconds[i][1])
	keyfirst = key.split()[0]
	keysecond = key.split()[1]
	if re.match(r'^<https?:\/\/.+\|?.*>$', keyfirst):
		keyfirst = keyfirst[1:-1]
		if '|' in keyfirst:
			keyfirst = keyfirst.split('|')[1]
	if re.match(r'^<https?:\/\/.+\|?.*>$', keysecond):
		keysecond = keysecond[1:-1]
		if '|' in keysecond:
			keysecond = keysecond.split('|')[1]
	newkey = keyfirst + ' ' + keysecond
	newdict[newkey] = (firsts, seconds)

output = open('Markov_Dict.pkl', 'w')
pickle.dump(newdict, output)
output.close()
"""
