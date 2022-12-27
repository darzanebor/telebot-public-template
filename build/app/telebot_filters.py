#!/usr/bin/env python3
import re
import json
import logging
import telebot.types
from os import environ as env
import telebot.asyncio_filters
from telebot import asyncio_handler_backends

class MessageMiddleware(asyncio_handler_backends.BaseMiddleware):
    """ Preprocess Message """
    def __init__(self):
        self.update_types = ["message"]
    async def pre_process(self, message, data):
        pass
    async def post_process(self, message, data, exception):
        if exception:
            logging.error(str(exception))


class ChatValidationFilter(telebot.asyncio_filters.SimpleCustomFilter):
    """ Chat Validation Filter """
    key = "chat_authorized"
    @staticmethod
    async def check(message: telebot.types.Message):
        return message.chat.id in json.loads(env.get("JIMMY_ALLOWED_CHAT"))


class IoTValidationFilter(telebot.asyncio_filters.SimpleCustomFilter):
    """ IoT Validation Filter """
    key = "iot_message"
    @staticmethod
    async def check(message: telebot.types.Message):
        pattern = re.compile(r"^\s*(включить|выключить|вкл|выкл)", re.IGNORECASE)
        match = re.search(pattern, message.text)
        if match:
            return True
        return False


class MagnetValidationFilter(telebot.asyncio_filters.SimpleCustomFilter):
    """ Magnet Validation Filter """
    key = "magnet_message"
    @staticmethod
    async def check(message: telebot.types.Message):
        pattern = re.compile(r"magnet:\?xt=urn:[a-z0-9]+:[a-zA-Z0-9]{32}")
        match = re.search(pattern, message.text)
        if match:
            return True
        return False
