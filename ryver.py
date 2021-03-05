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
    def __init__(self, client, domain, username, password, export_dir):
        self.domain = domain
        self.client = client
        self.base = f"https://{domain}/api/1/odata.svc"
        self.username = username
        self.password = password
        self.export_dir = os.path.expanduser(export_dir)

        self.export_dirs = {
            "users": os.path.join(self.export_dir, "users"),
            "teams": os.path.join(self.export_dir, "teams"),
            "forums": os.path.join(self.export_dir, "forums"),
        }

        for d in self.export_dirs.values():
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

    async def fetch_chat(self, kind, path, id, name, limit):
        global logger
        logger.info(f"Fetching chat from {kind} {name} ({id})")

        dump_file = os.path.join(self.export_dirs[kind], f"{id}-{clean(name)}.json")

        try:
            with open(dump_file) as fp:
                data = json.load(fp)
            last_id = data[-1]["id"]
            when = data[-1]["when"]
            logger.info(f"Restarting {kind} {name} from {when} (id={last_id})")
        except:
            data = []
            last_id = None

        url = f"{self.base}/{path}({id})"

        while True:
            messages, last_id = await self.chat_history(url, last_id, limit)

            if last_id is None:
                break

            logger.info(f"{kind} - {name} (ID={id}): found {len(messages)} messages")
            data.extend(messages)

            with open(dump_file, "w") as fp:
                json.dump(data, fp, indent=2, sort_keys=True)

        logger.info(f"Finished with {kind}: {name}")


def clean(value):
    return "".join(
        c if c in string.ascii_letters or c.isdigit() else "-" for c in value
    )


def parse_ignores(rules):
    ignores = {
        "users": [],
        "teams": [],
        "forums": [],
    }

    for rule in rules:
        kind, value = rule.split("=", 1)
        kind += "s"

        if kind not in ignores:
            raise ValueError("Ignore only support {}".format(
                ", ".join(sorted(ignores))))

        try:
            value = int(value)
        except:
            raise ValueError("Ignore accept <kind>=<id>")

        ignores[kind].append(value)

    return ignores

async def main(args):
    ignores = parse_ignores(args.ignores)

    async with httpx.AsyncClient() as client:
        await export(client, args.export_dir, args.domain, args.username, args.password, ignores, args.messages_quantity)


async def export(client, export_dir, domain, username, password, ignores, limit):
    ryver = Ryver(client, domain, username, password, export_dir)
    await ryver.login()
    info = await ryver.info()

    tasks = []

    x = {
        "users": ("username", "users"),
        "teams": ("descriptor", "workrooms"),
        "forums": ("descriptor", "forums"),
    }

    for kind, (name_key, path) in x.items():
        for e in info[kind]:
            id = e["id"]
            name = e[name_key]
            if id in ignores[kind]:
                logger.warning(f"skipping {kind} '{name}' ID={id}, as requested")
                continue

            task = asyncio.create_task(ryver.fetch_chat(kind, path, id, name, limit))
            tasks.append(task)

    await asyncio.gather(*tasks)


parser = argparse.ArgumentParser()
parser.add_argument("export_dir", help="Where to export the data")
parser.add_argument("domain", help="The Ryver domain to use")
parser.add_argument("username", help="The username to authenticate with")
parser.add_argument("password", help="The password of that username")
parser.add_argument("-i", "--ignore", action="append", default=[], dest="ignores",
    help="Don't export specific teams, forums or users."
)
parser.add_argument("-m", "--messages-quantity", default=1000, type=int,
    help="Quantity of messages to fetch at once"
)
args = parser.parse_args()

asyncio.run(main(args))
