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
	newkey = key
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
	if re.match(r'^<https?:\/\/.+\|?.*>$', key):
		newkey = newkey[1:-1]
		if '|' in newkey:
			newkey = newkey.split('|')[1]
	newdict[newkey] = (firsts, seconds)

output = open('Markov_Dict.pkl', 'w')
pickle.dump(newdict, output)
output.close()
"""
