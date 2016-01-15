import threading
import os.path
import signal

from MarkovBot import MarkovBot


def main():
    config_path = "slackov.cfg"

    config_default = "slacktoken,\n" \
        "slackid,\n" \
        "avatarsource,\n" \
        "twitterconsumerkey,\n" \
        "twitterconsumersecret,\n" \
        "twitteraccesstoken,\n" \
        "twitteraccesssecret,\n" \
        "twitterid,"

    if os.path.isfile(config_path):
        config_vals = {}
        config_file = open(config_path, 'r')
        for line in config_file:
            try:
                (key, val) = line.split(',')
                if key:
                    key = key.strip()
                if val:
                    val = val.strip()
                config_vals[key] = val
            except ValueError:
                error_message = "Config file not properly setup. " \
                                "Config: {} missing {} value.\n"
                print error_message.format(config_path, line.replace(':', ''))

        slack = {
            "token": config_vals['slacktoken'],
            "id": config_vals['slackid'],
            "avatarsource": config_vals['avatarsource']
        }
        twitter = {
            "consumer_key": config_vals['twitterconsumerkey'],
            "consumer_secret": config_vals['twitterconsumersecret'],
            "access_token": config_vals['twitteraccesstoken'],
            "access_token_secret": config_vals['twitteraccesssecret'],
            "id": config_vals['twitterid']
        }

        if None in (slack['token'],
                    slack['id'],
                    slack['avatarsource']):
            print "Config file not properly setup. " \
                    "Config file located at {}.\n".format(config_path)
        else:
            bot = MarkovBot(None, slack, twitter)
            signal.signal(signal.SIGINT, bot.signal_handler)
            bot.start()

            bot.process.join()
            print threading.enumerate()

    else:
        print "Could not find a config file. " \
                "Creating a new one: {}\n".format(config_path)
        config_file = open(config_path, 'a')
        config_file.write(config_default)
        config_file.close()

if __name__ == "__main__":
    main()
