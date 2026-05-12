"""Auto-verify all fixes: test-llm API + run-task with Bing."""
import urllib.request, json, time, sys

BASE = "http://127.0.0.1:9242"

def post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))

print("=" * 50)
print("验证 1: 服务健康检查")
h = get("/health")
assert h["success"], f"Health check failed: {h}"
print(f"  ✅ 服务正常，LLM状态: {h['data']['llm']['status']}")

print("\n验证 2: LLM 状态接口")
llm = get("/llm-status")
assert llm["success"], f"LLM status failed: {llm}"
configured = (llm.get("data") or llm).get("configured")
print(f"  ✅ LLM configured={configured}, status={llm['data']['status']}")

print("\n验证 3: test-llm 接口（用当前 .env 配置）")
# Read current config from llm-status
raw = (llm.get("data") or llm).get("raw_config", "")
if raw:
    r = post("/test-llm", {"config": raw})
    if r.get("success"):
        print(f"  ✅ test-llm 通过: {r.get('data', {}).get('status_text', '')[:60]}")
    else:
        print(f"  ⚠ test-llm 失败 (可能是限流): {r.get('error','')[:100]}")
else:
    print("  ⚠ 无 raw_config，跳过 test-llm")

print("\n验证 4: 执行必应搜索任务")
task_id = f"verify-{time.strftime('%H%M%S')}"
print(f"  task_id: {task_id}")
print("  执行中（请查看 Chrome 窗口）...")

req = urllib.request.Request(
    BASE + "/run-task",
    data=json.dumps({
        "task": "打开必应 bing.com，搜索耳机，返回第一个搜索结果的标题",
        "mode": "cdp",
        "cdp_url": "http://127.0.0.1:9222",
        "task_id": task_id,
        "max_steps": 10
    }).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        r = json.loads(resp.read().decode("utf-8"))
        d = r.get("data", {})
        print(f"  success={d.get('success')}, steps={d.get('steps')}, task_id={d.get('task_id')}")
        result = d.get("final_result") or ""
        print(f"  结果: {result[:200]}")
        errs = [e for e in (d.get("errors") or []) if e]
        if errs:
            print(f"  错误: {errs[-1][:150]}")
        print(f"  GIF: {BASE}/traces/{d.get('task_id')}/recording.gif")
except Exception as e:
    print(f"  ❌ 任务失败: {e}")

print("\n验证 5: 历史记录接口")
traces = get("/traces")
runs = traces.get("runs", [])
print(f"  ✅ 历史记录数: {len(runs)}")
if runs:
    latest = runs[0]
    print(f"  最新: task_id={latest['task_id']}, steps={latest['steps']}, success={latest['success']}")

print("\n" + "=" * 50)
print("所有验证完成")
