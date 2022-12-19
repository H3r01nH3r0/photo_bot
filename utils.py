from json import load, dump
from io import BytesIO
import string
import random


def get_config(filename: str) -> dict:
    with open(filename, "r", encoding="utf-8") as file:
        data: dict = load(file)
    return data


def str2file(text: str, filename: str) -> BytesIO:
    file = BytesIO(text.encode())
    file.name = filename
    file.seek(0)
    return file

def save_config(filename: str, data: dict) -> None:
    for key in data.keys():
        if len(key) == 2:
            del data[key]
    with open(filename, "w", encoding="utf-8") as file:
        dump(data, file, indent=4, ensure_ascii=False)
