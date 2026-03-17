#!/usr/bin/env python3

from pathlib import Path
import time
import requests
import subprocess
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

CONFIG_PATH = os.path.expanduser("~/projects/wallpaper-daemon/config.json")
TEMP_PATH = Path("/tmp/unsplash_wallpaper.jpg")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def ensure_dir(path: Path):
    os.makedirs(path, exist_ok=True)


def resize_to_target(path: Path, resolution: str):
    target_w, target_h = map(int, resolution.split("x"))

    img = Image.open(path)
    src_w, src_h = img.size

    # scale to cover (no stretching)
    scale = max(target_w / src_w, target_h / src_h)
    new_size = (int(src_w * scale), int(src_h * scale))

    img = img.resize(new_size, Image.Resampling.LANCZOS)

    # center crop
    left = (img.width - target_w) // 2
    top = (img.height - target_h) // 2
    right = left + target_w
    bottom = top + target_h

    img = img.crop((left, top, right, bottom))

    img.save(path, quality=95)


def fetch_wallpaper(query: str, api_key: str, resolution: str):
    logging.info(f"Fetching wallpaper | query='{query}'")

    url = "https://api.unsplash.com/photos/random"

    headers = {"Authorization": f"Client-ID {api_key}"}

    params = {"query": query, "orientation": "landscape"}

    res = requests.get(url, headers=headers, params=params)

    if res.status_code != 200:
        logging.error(f"Unsplash API failed: {res.text}")
        raise Exception(res.text)

    data = res.json()

    # highest quality available
    image_url = data["urls"]["full"]

    logging.info("Downloading high-resolution image")

    img_data = requests.get(image_url).content

    with open(TEMP_PATH, "wb") as f:
        f.write(img_data)

    resize_to_target(TEMP_PATH, resolution)

    logging.info(f"Image processed to {resolution}")

    return TEMP_PATH


def save_to_history(src_path: Path, save_dir: Path):
    ensure_dir(save_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(save_dir, f"wallpaper_{timestamp}.jpg")

    with open(src_path, "rb") as src, open(dest_path, "wb") as dst:
        dst.write(src.read())

    logging.info(f"Saved to history: {dest_path}")
    logging.info(f"Total wallpapers: {len(os.listdir(save_dir))}")

    return dest_path


def enforce_history_limit(save_dir, limit):
    files = sorted(
        [os.path.join(save_dir, f) for f in os.listdir(save_dir)],
        key=os.path.getmtime,
        reverse=True,
    )

    removed = 0
    for f in files[limit:]:
        os.remove(f)
        removed += 1

    if removed > 0:
        logging.info(f"Removed {removed} old wallpapers")


def set_wallpaper(path):
    uri = f"file://{path}"

    subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri]
    )

    subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri]
    )

    logging.info(f"Wallpaper applied: {path}")


def main():
    logging.info("Starting Unsplash wallpaper daemon")

    last_mtime = 0
    config = load_config()
    api_key: str | None = os.getenv("UNSPLASH_ACCESS_KEY")
    if api_key:
        config["api_key"] = api_key
        logging.info("API key loaded from environment variable")

    while True:
        try:
            mtime = os.path.getmtime(CONFIG_PATH)
            if mtime != last_mtime:
                config = load_config()
                if api_key:
                    config["api_key"] = api_key
                last_mtime = mtime
                logging.info("Config reloaded")

            img_path = fetch_wallpaper(
                config["query"], config["api_key"], config["resolution"]
            )

            history_path = save_to_history(
                img_path, os.path.expanduser(config["save_dir"])
            )

            enforce_history_limit(
                os.path.expanduser(config["save_dir"]), config["history_size"]
            )

            set_wallpaper(history_path)

            logging.info(f"Sleeping for {config['interval']} minutes")
            time.sleep(config["interval"] * 60)

        except Exception:
            logging.exception("Cycle failed")
            time.sleep(30)


if __name__ == "__main__":
    main()
