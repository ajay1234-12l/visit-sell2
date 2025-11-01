# api/storage.py
import json, os
from threading import Lock
from .config import CFG

_lock = Lock()

def ensure_files():
    os.makedirs(CFG["DATA_DIR"], exist_ok=True)
    # tasks file is a list of task objects
    if not os.path.exists(CFG["TASKS_FILE"]):
        with open(CFG["TASKS_FILE"], "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
    if not os.path.exists(CFG["SETTINGS_FILE"]):
        with open(CFG["SETTINGS_FILE"], "w", encoding="utf-8") as f:
            json.dump({"accum_mode": CFG["ACCUM_MODE"]}, f, indent=2)

def read_tasks():
    ensure_files()
    with _lock:
        with open(CFG["TASKS_FILE"], "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []

def write_tasks(tasks):
    ensure_files()
    tmp = CFG["TASKS_FILE"] + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, default=str)
        os.replace(tmp, CFG["TASKS_FILE"])

def read_settings():
    ensure_files()
    with _lock:
        with open(CFG["SETTINGS_FILE"], "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {"accum_mode": CFG["ACCUM_MODE"]}

def write_settings(s):
    ensure_files()
    tmp = CFG["SETTINGS_FILE"] + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, default=str)
        os.replace(tmp, CFG["SETTINGS_FILE"])