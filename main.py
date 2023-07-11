# mod AutoPosting to Telegram for TorrentPier-II 2.1.5 alpha
# ver 1.0 by dr_brown

import pymysql.cursors
import re
import telebot
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from time import sleep

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
             '/ (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'

interval = 30  # posting interval in minutes
min_len_descr = 20  # min description length

db_connect = dict(host='db_ip', user='db_user', password='db_password', db='db_name', charset='utf8mb4',
                  cursorclass=pymysql.cursors.DictCursor)

connection = pymysql.connect(**db_connect)

tokenBot = ""  # your bot token from BotPather
chanelId = 0  # id telegram chanel: -int()
sampleUrl = "https:// <your domen> /viewtopic.php?t="

"""option 1 or option 2 comment / uncomment request"""
def getDataFromDB(cursor):

    """option 1, posts the latest releases in the last n minutes, the interval is set interval variable"""

    sql = "SELECT topic_id, topic_title, post_text FROM bb_bt_torrents LEFT JOIN bb_topics USING (topic_id) " \
          "LEFT JOIN bb_posts_text USING (post_id) WHERE pic_replace = 0 AND reg_time > UNIX_TIMESTAMP(DATE_SUB(NOW(" \
          f"), INTERVAL {interval} MINUTE))"

    """option 2, selects 10 releases from the database, and posts to telegram. interval configurable by cron. 
                                        attention! very very heavy database query"""

    # sql = "SELECT topic_id, topic_title, post_text FROM bb_bt_torrents LEFT JOIN bb_topics USING (topic_id) " \
    #       "LEFT JOIN bb_posts_text USING (post_id) WHERE pic_replace = 0 ORDER BY RAND() LIMIT 10"

    cursor.execute(sql)
    data = [(result['topic_id'], result['topic_title'], result['post_text']) for result in
            cursor.fetchall()]
    return data

def modificateData(data):
    new_data = []
    bad_data = []
    pattern_img_1 = r"\[img=right\](.*?)\[/img\]"
    pattern_img_2 = r"\[img\](.*?)\[/img\]"
    pattern_descr = r"\S*Описание\S*:\s*([^\n\r[]+)|\S*Описание:\S*\s*([^\n\r[]+)"

    for elem in data:
        matches_1 = re.findall(pattern_img_1, elem[2])
        matches_2 = re.findall(pattern_img_2, elem[2])
        if matches_1:
            url_image = matches_1[0]
        elif matches_2:
            url_image = matches_2[0]
        else:
            bad_data.append((elem[0],))
            continue
        match = re.search(pattern_descr, elem[2])
        if match:
            if match.group(1) is None or len(match.group(1)) < min_len_descr:
                if match.group(2) is None or len(match.group(2)) < min_len_descr:
                    bad_data.append((elem[0],))
                    continue
                else:
                    clear_descr = match.group(2)
            else:
                clear_descr = match.group(1)

            new_data.append((elem[0], elem[1], url_image, clear_descr))
        else:
            bad_data.append((elem[0],))

    return new_data, bad_data

def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1

    markup.add(InlineKeyboardButton(text='Скачать', url=sampleUrl + str(id)))

    return markup

def convert_url_fastpic(url):
    pattern = r'i(\d+)\.fastpic\.org/big/\d+/\d+/(.+/)(.+)'
    match = re.search(pattern, url)
    split_url = str(url).partition("big")
    converted_url = "https://fastpic.org/view/" + str(match.group(1)) + str(split_url[2]) + ".html"
    result = converted_url.replace(str(match.group(2)), "")
    return result

def convert_url_imageban(url):
    split_url = str(url).partition("out")
    converted_url = "https://imageban.ru/show" + str(split_url[2])
    if 'jpg' in converted_url:
        return converted_url.replace(".jpg", "/jpg")
    elif 'png' in converted_url:
        return converted_url.replace(".png", "/png")
    elif 'jpeg' in converted_url:
        return converted_url.replace(".jpeg", "/jpeg")
    elif 'gif' in converted_url:
        return converted_url.replace(".gif", "/gif")
    elif 'bmp' in converted_url:
        return converted_url.replace(".bmp", "/bmp")
    return converted_url

def parse_html(parse_url):
    if 'fastpic.org' in parse_url:
        redirected_url = convert_url_fastpic(parse_url)
    elif 'imageban.ru' in parse_url:
        redirected_url = convert_url_imageban(parse_url)
    req = Request(redirected_url, headers={'User-Agent': user_agent})
    try:
        page = BeautifulSoup(urlopen(req).read().decode('UTF-8'), 'html.parser')
    except HTTPError:
        return None
    return page

def update_post(new_data, cursor):
    for elem in new_data:
        update_bt_torrents = "UPDATE bb_bt_torrents SET pic_replace = 1 WHERE topic_id = %s"
        cursor.execute(update_bt_torrents, (elem[0],))
        connection.commit()

if __name__ == '__main__':
    try:
        with connection.cursor() as cursor:
            data = getDataFromDB(cursor)
            new_data, bad_data = modificateData(data)

            if bad_data.count != 0:
                update_post(bad_data, cursor)

            bot = telebot.TeleBot(tokenBot)

            for elem in new_data:
                if 'ipicture.ru' in elem[2] \
                        or 'fastpic.ru' in elem[2] \
                        or 'imageban.ru' in elem[2] \
                        or 'radikal.ru' in elem[2] \
                        or 'postimg.cc' in elem[2] \
                        or 'lostpic.net' in elem[2]:
                    continue
                elif str(elem[2]).find("fastpic.org") != -1:
                    page = parse_html(elem[2])
                    if page is None:
                        continue
                    real_image = page.find('img', {'class': 'image img-fluid'}).get('src')
                elif str(elem[2]).find("imageban.ru/out") != -1:
                    page = parse_html(elem[2])
                    if page is None:
                        continue
                    real_image = page.find('img', {'id': 'img_main'}).get('data-original')
                else:
                    real_image = elem[2]
                message = telebot.formatting.format_text(
                    telebot.formatting.hbold(elem[1]),
                    telebot.formatting.hide_link(real_image),
                    elem[3],
                    separator='\n')

                bot.send_message(chanelId, message, parse_mode="html", reply_markup=gen_markup(elem[0]))
                sleep(3)

            update_post(new_data, cursor)
    finally:
        connection.close()