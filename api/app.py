# api/app.py
import os, uuid, json
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from .config import CFG
from .storage import read_tasks, write_tasks, read_settings, write_settings
from .worker import ensure_worker_for_task, resume_running_tasks_on_startup, run_one_iteration_for_all

# Start Flask
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "../templates"))
app.secret_key = CFG["SECRET_KEY"]

# Resume running tasks (in-process) on startup
resume_running_tasks_on_startup()

# ----------------- Helper -----------------
def find_task_by_id(tid):
    tasks = read_tasks()
    return next((x for x in tasks if x["id"] == tid), None)

# ----------------- Pages -----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("index.html", user=session["user"])

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        uname = request.form.get("username", "").strip()
        pwd = request.form.get("password", "").strip()
        if uname == CFG["ADMIN_USER"] and pwd == CFG["ADMIN_PASS"]:
            session["user"] = {"username": uname, "admin": True}
            return redirect(url_for("home"))
        # for simplicity we don't have per-user accounts beyond admin; store session anyway
        session["user"] = {"username": uname, "admin": False}
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ----------------- API: create/start/stop/status/list -----------------
@app.route("/api/task/create", methods=["POST"])
def api_task_create():
    if "user" not in session:
        return jsonify({"error":"auth required"}), 401
    uid = (request.form.get("uid") or "").strip()
    try:
        target = int(request.form.get("target") or 0)
    except:
        target = 0
    if not uid or target <= 0:
        return jsonify({"error":"uid and positive target required"}), 400

    tasks = read_tasks()
    tid = str(uuid.uuid4())
    t = {
        "id": tid,
        "uid": uid,
        "target": target,
        "accumulated": 0,
        "status": "running",
        "last_successful": None,
        "logs": [],
        "created_at": None,
        "updated_at": None
    }
    tasks.append(t)
    write_tasks(tasks)

    # ensure worker thread for this task in the current process, if environment allows
    ensure_worker_for_task(tid)

    return jsonify({"ok": True, "task_id": tid})

@app.route("/api/task/<tid>/stop", methods=["POST"])
def api_task_stop(tid):
    # allow admin or task creator (we don't enforce creator mapping here; session user must exist)
    if "user" not in session:
        return jsonify({"error":"auth required"}), 401
    tasks = read_tasks()
    t = next((x for x in tasks if x["id"] == tid), None)
    if not t:
        return jsonify({"error":"task not found"}), 404
    t["status"] = "stopped"
    write_tasks(tasks)
    return jsonify({"ok": True})

@app.route("/api/task/<tid>", methods=["GET"])
def api_task_get(tid):
    t = find_task_by_id(tid)
    if not t:
        return jsonify({"error":"not found"}), 404
    return jsonify(t)

@app.route("/api/tasks", methods=["GET"])
def api_tasks_list():
    ap = request.args.get("admin_pass")
    if ap != CFG["ADMIN_PASS"]:
        return jsonify({"error":"admin auth required"}), 401
    tasks = read_tasks()
    return jsonify({"tasks": tasks})

# worker-run endpoint (run one iteration for all running tasks)
@app.route("/api/worker/run", methods=["POST"])
def api_worker_run():
    ap = request.form.get("admin_pass", "")
    if ap and ap != CFG["ADMIN_PASS"]:
        return jsonify({"error":"bad admin_pass"}), 401
    # run one iteration for all tasks
    res = run_one_iteration_for_all()
    # also start local thread per running task for this process
    tasks = read_tasks()
    for t in tasks:
        if t.get("status") == "running":
            ensure_worker_for_task(t["id"])
    return jsonify(res)

# admin: set accumulation mode
@app.route("/api/admin/set_mode", methods=["POST"])
def api_admin_set_mode():
    ap = request.form.get("admin_pass", "")
    if ap != CFG["ADMIN_PASS"]:
        return jsonify({"error":"admin auth required"}), 401
    mode = request.form.get("mode")
    if mode not in ("add_reports", "add_increase"):
        return jsonify({"error":"invalid mode"}), 400
    s = read_settings()
    s["accum_mode"] = mode
    write_settings(s)
    return jsonify({"ok": True, "mode": mode})

# admin page
@app.route("/admin")
def admin_page():
    if "user" not in session or not session["user"].get("admin"):
        return "Access denied"
    return render_template("admin.html", admin_user=CFG["ADMIN_USER"])

# static health endpoint
@app.route("/api/health")
def health():
    return jsonify({"ok": True})

# run only if executed directly (not under serverless)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)