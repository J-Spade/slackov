# slackov

# Setup

(Instructions below use bash, use equivalent commands in Windows land)

1. Clone this repository.
2. Make sure you have [Python 2.7.11](https://www.python.org/downloads/) and [pip](https://pip.pypa.io/en/stable/) installed.
3. Install slackclient and tweepy using pip.
        ```
        pip install slackclient
        pip install tweepy
        ```
4. Replace the `_client.py` file in the `slackclient` install directory with the one from this repository.
        ```
        pip show slackclient
        cp -f /path/to/slackclient/_client.py /path/to/local/repo/_client.py
        ```
5. Run the program for the first time. It will fail hard and create a `slackov.cfg` configuration file. Enter the appropriate value next to the comma for each key.
        ```
        python runSlackov.py
        ```