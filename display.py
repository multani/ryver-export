#!/usr/bin/env python3

import argparse
from blessings import Terminal
import json


t = Terminal()

def read(message, indentplus):
    from_ = message["from"]["__descriptor"]
    when =  message["when"][:19]
    text =  message["body"]

    sep = "\n"
    if text.count(sep) > 0:
        # indent = len(from_) + len(when) + indentplus
        indent = len(when) + indentplus

        lines = text.split(sep)

        res = [lines[0]]
        for line in lines[1:]:
            res.append((" " * indent) + line)

        text = sep.join(res)

    return from_, when, text

def display(content):
    for m in content:
        from_, when, text = read(m, 2)

        print(
            t.dim + when + t.normal +
            ": " + t.bold + t.green + from_ + t.normal +
            t.dim + " --" + t.normal,
            text
        )

def main(args):
    with open(args.filename) as fp:
        data = json.load(fp)

    display(data)


parser = argparse.ArgumentParser()
parser.add_argument("filename")
args = parser.parse_args()

main(args)
