from MarkovBotTwo import MarkovBot
import time
import threading
import os.path

config_path = "slackov.cfg"

config_default = "token,\nid,\navatarsource,"

if os.path.isfile(config_path):
    config_vals = dict()
    config_file = open(config_path, 'r')
    for line in config_file:
        try:
            (key, val) = line.split(',')
            config_vals[key] = val
        except ValueError as e:
            print "Config file not properly setup. Config: {} missing {} value.\n".format(config_path, line.replace(':',''))
    
    if None in (config_vals['token'], config_vals['id'], config_vals['avatarsource']):
        print "Config file not properly setup. Config file located at {}.\n".format(config_path)
    else:
        bot = MarkovBot(config_vals['token'].strip(), None, config_vals['id'].strip(), config_vals['avatarsource'].strip())
        bot.start()

        bot.process.join()
        print threading.enumerate()
        
else:
    print "Could not find a config file. Creating a new one: {}\n".format(config_path)
    config_file = open(config_path, 'a')
    config_file.write(config_default)
    config_file.close()