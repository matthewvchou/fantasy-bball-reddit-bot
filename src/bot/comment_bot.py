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
              'ftp'
              }

def process_comment(comment):
    '''Function to recognize callphrase to bot and '''
    # Phrase to summon
    summonphrase = '!fantasybot'
    # Logic to summon
    if comment.body.startswith(summonphrase):
        # TODO: need to put in scipt and other logic here
        ''' Break down into categories '''
        print('Replying to comment...')
        comment_reply(comment)

# TODO: Get Date and Run Script for Specific Date
def comment_reply(comment):
    '''Function that takes in all categories defined by user in bot call and outputs list of top players of that specific category'''
    text = 'Recognized:'
    categories = comment.body.split()
    print(categories)
    if not len(categories):
        print('No commands')
        return
    for cat in categories[1:]:
        if cat in CATEGORIES:
            text = text + ", "  + cat
        else:
            print('not recognized')
            # Input message here for not recognized command
            comment.reply(f'{cat} not recognized')
            return
    comment.reply(text)

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

    # Subreddit
    subreddit = reddit.subreddit("bballfanalyst")

    # Go through comments
    # NOTE: Will not stop running until manually stopped, free hosting somewhere?
    for comment in subreddit.stream.comments(skip_existing=True):
        process_comment(comment)


if __name__ == '__main__':
    main()