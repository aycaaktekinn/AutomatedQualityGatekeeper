"""Planted issues for the reference repository. Do not fix them."""
import os
import subprocess

API_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"


def run_command(user_input):
    return subprocess.call(user_input, shell=True)


def classify(a, b, c, d, e, f):
    if a:
        if b:
            return 1
        elif c:
            return 2
    elif d:
        for i in range(10):
            if i == e:
                return 3
            if i == f:
                return 4
    elif e and f:
        return 5
    elif a or b or c:
        return 6
    while d and e:
        if f:
            break
    return 0


def load(path):
    try:
        return open(path).read()
    except:
        pass


def parse(value):
    try:
        return int(value)
    except Exception:
        pass
