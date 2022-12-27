#!/usr/bin/env python3
""" python3 telegram bot with callback """
import json
import logging
import asyncio
from os import environ as env

import boto3
import telebot.types
from aiohttp import web
from telebot.async_telebot import AsyncTeleBot
from botocore.config import Config as botoConfig
from prometheus_client import multiprocess, generate_latest, Summary, CollectorRegistry
from prometheus_async.aio import time
from logging_formatter import SensitiveFormatter
from telebot_filters import (
    MessageMiddleware,
    ChatValidationFilter,
    IoTValidationFilter,
    MagnetValidationFilter,
)


HELP_TEMPLATE = "."
API_TOKEN = env.get("JIMMY_TELEGRAM_TOKEN")
WEBHOOK_HOST = env.get("JIMMY_WEBHOOK_HOST")
WEBHOOK_PATH = env.get("JIMMY_WEBHOOK_PATH")
WEBHOOK_URL_BASE = "https://{}".format(WEBHOOK_HOST)
WEBHOOK_CALLBACK_ROUTE = "{}/{}/".format(WEBHOOK_PATH, "{token}")
WEBHOOK_URL_PATH = "{}/{}/".format(WEBHOOK_PATH, API_TOKEN)
REQUEST_TIME = Summary("svc_request_processing_time", "Time spent processing request")

app = web.Application()
bot = AsyncTeleBot(API_TOKEN)


async def gen_template(filename):
    """ generate template from file """
    with open(filename) as file:
        message = file.read()
    return message


def child_exit(server, worker):
    """ multiprocess function for prometheus to track gunicorn """
    multiprocess.mark_process_dead(worker.pid)


async def handle_metrics(request):
    """ metrics handler """
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    metrics_data = (generate_latest(registry)).decode("utf-8")
    return web.Response(status=200, content_type="text/html", text=metrics_data)


async def handle_health(request):
    """ health check handler """
    return web.Response(status=200, content_type="text/html", text="200")


@time(REQUEST_TIME)
async def handle_callback(request):
    """ telegram callback handler """
    if request.match_info.get("token") == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        await bot.process_new_updates([update])
        return web.Response()
    return web.Response(status=403)


async def sqs_send_message(message, queue_url):
    """ Send message to SQS queue """
    try:
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=message)
    except Exception as error:
        logging.error("%s", error)


async def bot_send_message(message, chat_id, parse_mode=None):
    """ Send message to telegram """
    try:
        await bot.send_message(chat_id, message, parse_mode=parse_mode)
    except Exception as error:
        logging.error("%s", error)


@bot.message_handler(commands=["start", "help"], chat_authorized=True)
async def handle_commands(message):
    """ Provide help"""
    await bot_send_message(HELP_TEMPLATE, message.chat.id, parse_mode="HTML")
    logging.debug("Got message with id %i from %s", message.message_id, message.chat.id)


@bot.message_handler(iot_message=True, chat_authorized=True)
async def handle_iot_messages(message):
    """ IoT Actions handler """
    queue_url = env.get("JIMMY_IOT_QUEUE")
    await sqs_send_message(message.text, queue_url)
    await bot_send_message("Added IoT action to queue", message.chat.id)
    logging.debug("add iot action to queue: %s", message.text)
    logging.info("iot message id %i from %s", message.message_id, message.chat.id)


@bot.message_handler(magnet_message=True, chat_authorized=True)
async def handle_magnet_message(message):
    """ Magnet url handler """
    queue_url = env.get("JIMMY_SQS_QUEUE")
    await sqs_send_message(message.text, queue_url)
    await bot_send_message("Magnet url added to queue", message.chat.id)
    logging.debug("add magnet link to queue: %s", message.text)
    logging.info("magnet message id %i from %s", message.message_id, message.chat.id)


async def init_sqs():
    """ init sqs """
    global sqs_client
    sqs_client = boto3.client(
        service_name="sqs",
        endpoint_url=env.get("JIMMY_SQS_ENDPOINT"),
        aws_access_key_id=env.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY"),
        region_name="ru-central1",
        config=botoConfig(
            connect_timeout=45,
            read_timeout=90,
            retries={"max_attempts": 10, "mode": "standard"},
        ),
    )


async def init_filters():
    """ telegram filters init """
    bot.add_custom_filter(IoTValidationFilter())
    bot.add_custom_filter(ChatValidationFilter())
    bot.add_custom_filter(MagnetValidationFilter())
    bot.setup_middleware(MessageMiddleware())


async def init_routes():
    """ telegram routes init """
    app.router.add_get("/healthz", handle_health)
    app.router.add_get("/metrics", handle_metrics)
    app.router.add_post(WEBHOOK_CALLBACK_ROUTE, handle_callback)


async def init_log():
    """ telegram logging init """
    logging.basicConfig(
        level=logging.getLevelName(env.get("LOG_LEVEL", "INFO")),
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    for handler in logging.root.handlers:
        handler.setFormatter(
            SensitiveFormatter("JIMMY - %(levelname)s - %(asctime)s - %(message)s")
        )


async def init_templates():
    """ init templates """
    global HELP_TEMPLATE
    HELP_TEMPLATE = await gen_template("json/help.tmpl")


async def init():
    """ telegram main init """
    await init_sqs()
    await init_log()
    await init_routes()
    await init_filters()
    await init_templates()
    await (bot.remove_webhook())
    await (bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH))
    logging.info("%s", "ready to handle messages")


asyncio.run(init())
web.run_app(
    app,
    host=env.get("JIMMY_LISTEN_HOST", "0.0.0.0"),
    port=int(env.get("JIMMY_LISTEN_PORT", "5000")),
)
