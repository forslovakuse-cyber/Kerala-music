import json
import os

LANGS_FILE = json.load(open("langs.json"))
LANG = os.environ.get("BOT_LANG")
DOWNLOADING_USERS = []

TMP_DIR = "tmp"

# (connect, read) in seconds. The read timeout applies to each read, so long streams still work.
HTTP_TIMEOUT = (10, 60)

# Telegram bots cannot upload files over 50 MB
TELEGRAM_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


if LANG is not None:
    print("Lang : " + LANG)
else:
    print("Lang : en")
    LANG = "en"


def __(s):
    return LANGS_FILE[s][LANG]


def is_downloading(user_id):
    return user_id in DOWNLOADING_USERS


def add_downloading(user_id):
    DOWNLOADING_USERS.append(user_id)


def remove_downloading(user_id):
    DOWNLOADING_USERS.remove(user_id)
