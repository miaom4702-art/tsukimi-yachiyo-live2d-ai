# engine/storage.py

import json
from pathlib import Path


def load_json(path, default=None):

    file = Path(path)

    if not file.exists():

        return default

    with open(
        file,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(path, data):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )