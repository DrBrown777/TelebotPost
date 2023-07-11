# TelebotPost
AutoPosting last releases to Telegram chanel for TorrentPier-II

The mod allows you to take the latest posts, title, poster, description, link from the database and post to your telegram channel.

There are two modes of operation:
1. Posting releases added in the last 30 minutes (optional, cron must be synchronized with the interval set in the variable)
2. Ramdomly selects from the database, 10 posts, and posts to Telegram, by crowns, the interval is up to you (attention, this is a very heavy request, not recommended)

System requirements:
1. Python 3.7 and above
2. BeautifulSoup and PyMySQL libraries installed
3. Requires a bit field in the bb_bt_torents table that stores 0 or 1, I call it pic_replase, you can call it your own.

/*** Cron task run every 30 min ***/

/usr/bin/python3 /home/main.py

the main.py file should be located in the home folder or in any convenient place
