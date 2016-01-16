import pickle
import re

input = open('Markov_Dict.pkl', 'r')
dictionary = pickle.load(input)
input.close()

keystochange = []

for key in dictionary:
	firsts = dictionary.get(key)[0]
	for i in range (0, len(firsts)):
		if re.match(r'^<https?:\/\/.+\|?.*>$', firsts[i][0]):
			firsts[i][0] = firsts[i][0][1:-1]
			if '|' in firsts[i][0]:
				firsts[i][0] = firsts[i][0].split('|')[1]
	key[0] = firsts
	seconds = dictionary.get(key)[1]
	for i in range (0, len(seconds)):
		if re.match(r'^<https?:\/\/.+\|?.*>$', seconds[i][0]):
			seconds[i][0] = seconds[i][0][1:-1]
			if '|' in seconds[i][0]:
				seconds[i][0] = seconds[i][0].split('|')[1]
	key[1] = seconds
	if re.match(r'^<https?:\/\/.+\|?.*>$', key):
		keystochange.append(key)

for key in keystochange:
		newkey = key
		newkey = newkey[1:-1]
		if '|' in newkey:
			newkey = newkey.split('|')[1]
		dictionary[newkey] = dictionary.get(key)
		del dictionary[key]

output = open('Markov_Dict.pkl', 'w')
pickle.dump(self.dictionary, output)
output.close()
		