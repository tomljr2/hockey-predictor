import praw

#This is used for mysportsfeeds and reddit authentication
MSFUSERNAME = ""
MSFPASSWORD = ""

REDDITUSERNAME = ""
REDDITPASSWORD = ""

REDDIT = praw.Reddit(client_id="",
                     client_secret="",
                     user_agent="nhl-predict by /u/heavie1",
                     username=REDDITUSERNAME,
                     password=REDDITPASSWORD)
