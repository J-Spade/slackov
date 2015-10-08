from MarkovBot import MarkovBot
import time

token = "xoxb-12028329271-mhiX0egylVu0AQTxkQseKFhi"
id = "U0C0U9P7Z"
avatarsource = "https://twitter.com/unova_/status/650908303426494464"

bot = MarkovBot(token, None, id, avatarsource)
bot.start()