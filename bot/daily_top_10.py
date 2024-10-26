import os
from dotenv import load_dotenv
import praw

CATEGORIES = {'pts',
              'rb',
              'ast',
              'stl',
              'blk',
              '3pts',
              'fgp',
              'f'
            }

def main():

    # Getting env variables
    load_dotenv()

    # Configuring Bot
    reddit = praw.Reddit(
        client_id = os.getenv('MY_ID'),
        client_secret = os.getenv('MY_SECRET'),
        password = os.getenv('MY_PASSWORD'),
        user_agent = "testscript by u/bball-fanalyst",
        username = os.getenv('MY_USERNAME'),
    )
    print(reddit.user.me())

if __name__ == '__main__':
    main()