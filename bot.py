#! venv/bin/python3

import asyncio
from telethon import TelegramClient, events
import json
import sys
import logging
from pathlib import Path
import re
import aiohttp
import config as cfg


def create_logger(verbose=True, filename='', file_wipe=True):

    logFormatter = logging.Formatter('%(asctime)s %(message)s')
    logger = logging.getLogger()
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    if filename != '':
        if file_wipe:
            try:
                Path(filename).unlink()
            except:
                pass
        fileHandler = logging.FileHandler(filename)
        fileHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)
    return logger


async def bot():
    global client
    logger.info('Bot init')
    client = TelegramClient(cfg.session_name, cfg.api_id, cfg.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.sign_in(bot_token=cfg.bot_token)


    @client.on(events.NewMessage())
    async def new_message(event):
        text = event.message.text
        logger.info('Message: ' + json.dumps({
            'text': text,
            'chat_id': event.chat_id,
            'message_id': event._message_id
        }))
        if text != '':
            data = extract_data(text)
            if data:
                await call_webhook(data)


    await client.start()
    me = await client.get_me()
    logger.info('Bot ready, id ' + str(me.id))
    while 1:
        try:
            await client.run_until_disconnected()
        except ConnectionError:
            logger.info('Bot connection error, delay 60 sec')
            asyncio.sleep(60)
            logger.info('Bot retry')
            continue


def extract_data(text):
    match = re.search(
        '^(\w+)\n(buy|sell)\nmax per\: \d+(?:\.\d+)% atr\(\d+(?:\.\d+)%\)\nmin per\: \d+(?:\.\d+)% atr\(\d+(?:\.\d+)%\)',
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if match:
        data = {
            "name": cfg.webhook_name,
            "secret": cfg.webhook_secret,
            "side": match.groups()[1],
            "symbol": match.groups()[0],
        }
        return data


async def call_webhook(data):
    logger.info('Call webhook ' + json.dumps(data))
    async with aiohttp.ClientSession() as session:
        async with session.post(cfg.webhook_url, json=data) as resp:
            status = resp.status
            text = await resp.text()
            logger.info('Webhook response ' + str(status) + ' ' + text)


logger = create_logger(cfg.log_verbose, cfg.log_name, cfg.log_wipe_on_startup)
asyncio.run(bot())
