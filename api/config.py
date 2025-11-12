# api/config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# If running on Vercel, use /tmp for writable storage (ephemeral).
DEFAULT_DATA_DIR = os.environ.get("DATA_DIR") or ("/tmp/visits-tracker" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "data"))

CFG = {
    "DATA_DIR": DEFAULT_DATA_DIR,
    "TASKS_FILE": os.path.join(DEFAULT_DATA_DIR, "tasks.json"),
    "SETTINGS_FILE": os.path.join(DEFAULT_DATA_DIR, "settings.json"),
    # real visits API template
    "VISIT_API_TEMPLATE": os.environ.get("VISIT_API_TEMPLATE", "https://visit-api-by-digi.vercel.app/visit?uid={uid}&server_name=ind"),
    # default poll guidance (sec) — external pinger should call worker.run that often
    "SUGGESTED_PING_INTERVAL": int(os.environ.get("POLL_INTERVAL", "15")),
    # default accumulation mode: "add_reports" or "add_increase"
    "ACCUM_MODE": os.environ.get("ACCUM_MODE", "add_reports"),
    # admin credentials (change via env or here)
    "ADMIN_USER": os.environ.get("ADMIN_USER", "admin"),
    "ADMIN_PASS": os.environ.get("ADMIN_PASS", "1234"),
    # secret used for sessions (local only; in production set via env)
    "SECRET_KEY": os.environ.get("SECRET_KEY", "change_me_very_secret"),
}
