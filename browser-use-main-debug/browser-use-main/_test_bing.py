import urllib.request, json, time

task = "打开必应搜索 bing.com，搜索耳机，查看前3个结果"
task_id = f"bing-test-{time.strftime('%H%M%S')}"

body = json.dumps({
    "task": task,
    "mode": "cdp",
    "cdp_url": "http://127.0.0.1:9222",
    "task_id": task_id,
    "max_steps": 15
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:9242/run-task",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST"
)

print(f"task_id : {task_id}")
print(f"task    : {task}")
print("执行中，请查看 Chrome 窗口...\n")

try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        r = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:300]}")
    exit(1)
except Exception as e:
    print(f"请求失败: {e}")
    exit(1)

print("=" * 55)
if not r.get("success"):
    print(f"❌ 失败: {r.get('error', '未知错误')}")
else:
    d = r.get("data") or {}
    ok = d.get("success", False)
    print(f"{'✅' if ok else '⚠'} success : {ok}")
    print(f"   steps   : {d.get('steps', 0)}")
    print(f"   task_id : {d.get('task_id', '')}")
    result = d.get("final_result") or ""
    print(f"   result  : {result[:400]}")
    errs = d.get("errors") or []
    if errs:
        print(f"   errors  : {errs[-1][:200]}")
    tid = d.get("task_id", "")
    if tid:
        print(f"\n🎬 GIF  : http://127.0.0.1:9242/traces/{tid}/recording.gif")
        print(f"📄 日志 : http://127.0.0.1:9242/traces/{tid}/conversation.json")
        print(f"📂 历史 : http://127.0.0.1:9242/traces")
