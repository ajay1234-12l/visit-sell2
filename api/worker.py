# api/worker.py
import threading, time, traceback
import urllib.request, json
from .storage import read_tasks, write_tasks, read_settings
from .config import CFG

# In-process thread map
THREADS = {}
THREADS_LOCK = threading.Lock()

# small helper to call visit API
def call_visit_api(uid):
    url = CFG["VISIT_API_TEMPLATE"].format(uid=uid)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VisitsTracker/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            try:
                js = json.loads(raw)
            except:
                js = {"raw": raw}
            succ = None
            if isinstance(js, dict):
                succ = js.get("SuccessfulVisits")
                try:
                    if succ is not None:
                        succ = int(succ)
                except:
                    pass
            return {"ok": True, "api": js, "SuccessfulVisits": succ}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# worker function that loops for one task as long as its status == running
def task_worker(task_id):
    try:
        while True:
            tasks = read_tasks()
            t = next((x for x in tasks if x["id"] == task_id), None)
            if not t:
                break
            if t.get("status") != "running":
                break

            # call API
            res = call_visit_api(t["uid"])
            succ = res.get("SuccessfulVisits") if res.get("ok") else None
            succ_num = 0
            if succ is not None:
                try:
                    succ_num = int(succ)
                except:
                    succ_num = 0

            settings = read_settings()
            accum_mode = settings.get("accum_mode", CFG["ACCUM_MODE"])

            if accum_mode == "add_reports":
                add = succ_num
            else:  # add_increase
                last = t.get("last_successful")
                if last is None:
                    add = succ_num
                else:
                    add = max(0, succ_num - (last or 0))

            t["accumulated"] = int(t.get("accumulated", 0)) + int(add or 0)
            t["last_successful"] = succ_num
            t.setdefault("logs", []).append({
                "time": now_iso(),
                "success_value": succ_num,
                "added": add,
                "api": res.get("api")
            })
            t["updated_at"] = now_iso()

            if t["accumulated"] >= int(t["target"]):
                t["status"] = "completed"
                t["completed_at"] = now_iso()

            write_tasks(tasks)
            # short sleep to avoid hammering in same process; external pinger frequency controls overall cadence
            time.sleep(1)
    except Exception as e:
        print("task_worker error:", e)
        traceback.print_exc()
    finally:
        with THREADS_LOCK:
            THREADS.pop(task_id, None)

# spawn worker thread for a task id if not already running in-process
def ensure_worker_for_task(task_id):
    with THREADS_LOCK:
        if task_id in THREADS:
            return
        th = threading.Thread(target=task_worker, args=(task_id,), daemon=True)
        THREADS[task_id] = th
        th.start()

# resume existing running tasks on startup
def resume_running_tasks_on_startup():
    tasks = read_tasks()
    for t in tasks:
        if t.get("status") == "running":
            ensure_worker_for_task(t["id"])

# public function: run one iteration for all running tasks (used by /api/worker/run)
def run_one_iteration_for_all():
    tasks = read_tasks()
    settings = read_settings()
    accum_mode = settings.get("accum_mode", CFG["ACCUM_MODE"])
    results = []
    processed = 0
    for t in tasks:
        if t.get("status") != "running": 
            continue
        processed += 1
        res = call_visit_api(t["uid"])
        succ = res.get("SuccessfulVisits")
        try:
            succ_num = int(succ) if succ is not None else 0
        except:
            succ_num = 0

        if accum_mode == "add_reports":
            add = succ_num
        else:
            last = t.get("last_successful")
            if last is None:
                add = succ_num
            else:
                add = max(0, succ_num - (last or 0))

        t["accumulated"] = int(t.get("accumulated", 0)) + int(add or 0)
        t["last_successful"] = succ_num
        t.setdefault("logs", []).append({
            "time": now_iso(),
            "success_value": succ_num,
            "added": add,
            "api": res.get("api")
        })
        t["updated_at"] = now_iso()
        if t["accumulated"] >= int(t["target"]):
            t["status"] = "completed"
            t["completed_at"] = now_iso()
        results.append({"id": t["id"], "uid": t["uid"], "added": add, "accumulated": t["accumulated"], "status": t["status"]})
    write_tasks(tasks)
    return {"processed": processed, "results": results, "accum_mode": accum_mode}