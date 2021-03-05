#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import string
from urllib import parse

import httpx
from loguru import logger


class Ryver:
    def __init__(self, client, domain, username, password, dump_dir):
        self.domain = domain
        self.client = client
        self.base = f"https://{domain}/api/1/odata.svc"
        self.username = username
        self.password = password
        self.dump_dir = os.path.expanduser(dump_dir)

        self.dump_dirs = {
            "users": os.path.join(self.dump_dir, "users"),
            "workrooms": os.path.join(self.dump_dir, "teams"),
            "forums": os.path.join(self.dump_dir, "forums"),
        }

        for d in self.dump_dirs.values():
            os.makedirs(d, exist_ok=True)

    async def login(self):
        url = f"https://{self.domain}/application/login"
        data = {
            "username": self.username,
            "password": self.password,
            "rememberme": "on",
        }
        logger.info(f"Logging in as {self.username}")
        x = await self.client.post(url, data=data)
        x.raise_for_status()
        logger.info("Logged in!")

    async def info(self):
        qs = {"$format": "json"}
        url = "{}?{}".format(f"{self.base}/Ryver.Info()", parse.urlencode(qs))
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        return data["d"]

    async def chat_history(self, url, last_id, limit=1000):
        qs = {
            "$format": "json",
            "$top": f"{limit}",
            "$orderby": "when asc",
            "$inlinecount": "allpages",
        }
        if last_id:
            qs["$filter"] = f"id gt '{last_id}'"

        url = "{}/Chat.History()?{}".format(url, parse.urlencode(qs))
        for i in range(1, 10):
            try:
                response = await self.client.get(url)
            except Exception as exc:
                logger.warning(f"error: {exc} (try {i}, will retry in 1 second)")
                await asyncio.sleep(1)
                continue
            else:
                break
        else:
            logger.error("ohoh")

        response.raise_for_status()
        data = response.json()

        count = data["d"]["__count"]
        if count <= 0:
            return [], None

        messages = data["d"]["results"]
        last_id = messages[0]["id"]

        return messages, last_id

    async def fetch(self, what, id, name):
        global logger
        logger.info(f"Fetching messages from {what} {name} ({id})")
        dump_file = os.path.join(self.dump_dirs[what], f"{id}-{name}.json")

        try:
            with open(dump_file) as fp:
                data = json.load(fp)
            last_id = data[-1]["id"]
            when = data[-1]["when"]
            logger.info(f"Restarting {what} {name} from {when} (id={last_id})")
        except:
            data = []
            last_id = None

        url = f"{self.base}/{what}({id})"

        while True:
            messages, last_id = await self.chat_history(url, last_id)

            if last_id is None:
                break

            logger.info(f"{name}: found {len(messages)} messages")
            data.extend(messages)

            with open(dump_file, "w") as fp:
                json.dump(data, fp, indent=2, sort_keys=True)


def clean(value):
    return "".join(
        c if c in string.ascii_letters or c.isdigit() else "-" for c in value
    )


async def main(dump_dir, domain, username, password):
    async with httpx.AsyncClient() as client:
        await export(client, dump_dir, domain, username, password)


async def export(client, dump_dir, domain, username, password):
    ryver = Ryver(client, domain, username, password, dump_dir)
    await ryver.login()
    info = await ryver.info()

    tasks = []

    for e in info["users"]:
        id = e["id"]
        name = e["username"]
        task = asyncio.create_task(ryver.fetch("users", id, name))
        tasks.append(task)

    for e in info["teams"]:
        id = e["id"]
        name = "".join(clean(e["descriptor"]))
        task = asyncio.create_task(ryver.fetch("workrooms", id, name))
        tasks.append(task)

    for e in info["forums"]:
        id = e["id"]
        name = "".join(clean(e["descriptor"]))
        task = asyncio.create_task(ryver.fetch("forums", id, name))
        tasks.append(task)

    await asyncio.gather(*tasks)


parser = argparse.ArgumentParser()
parser.add_argument("dump_dir")
parser.add_argument("domain")
parser.add_argument("username")
parser.add_argument("password")
args = parser.parse_args()

asyncio.run(main(args.dump_dir, args.domain, args.username, args.password))
