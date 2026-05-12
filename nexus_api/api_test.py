"""
NexusAgent API 测试服务
提供 YAML 驱动的接口测试能力
"""
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────
# 模型定义
# ─────────────────────────────────────────────────────────────────────────────

class RunTestRequest(BaseModel):
    yaml: str
    env: str = "aliyun"


class TestResult(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class EnvConfig(BaseModel):
    name: str
    base_url: str
    description: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 环境配置
# ─────────────────────────────────────────────────────────────────────────────

ENVIRONMENTS = {
    "aliyun": EnvConfig(name="阿里云", base_url="https://api-c.soboten.com"),
    "tencent": EnvConfig(name="腾讯云", base_url="https://api-c.soboten.com"),
    "sg": EnvConfig(name="新加坡", base_url="https://sg-api-c.soboten.com"),
    "us": EnvConfig(name="美国", base_url="https://us-api-c.soboten.com"),
}


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI 应用
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="NexusAgent API Testing Service",
        description="YAML 驱动的接口测试服务",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "api_test"}

    @app.post("/run", response_model=TestResult)
    async def run_test(request: RunTestRequest):
        """执行 YAML 测试用例"""
        import yaml
        import httpx

        start_time = time.time()

        try:
            # 解析 YAML
            test_case = yaml.safe_load(request.yaml)
            if not test_case:
                return TestResult(success=False, error="YAML 解析失败")

            config = test_case.get("config", {})
            base_url = config.get("base_url", "https://httpbin.org")
            teststeps = test_case.get("teststeps", [])

            if not teststeps:
                return TestResult(success=False, error="无测试步骤")

            output_lines = []
            all_success = True

            async with httpx.AsyncClient(timeout=30.0) as client:
                extracted_vars = {}

                for i, step in enumerate(teststeps, 1):
                    step_name = step.get("name", f"Step {i}")
                    request_cfg = step.get("request", {})

                    method = request_cfg.get("method", "GET").upper()
                    url = request_cfg.get("url", "/")
                    full_url = f"{base_url}{url}"

                    output_lines.append(f"\n[{i}] {step_name}")
                    output_lines.append(f"    {method} {full_url}")

                    try:
                        response = await client.request(
                            method=method,
                            url=full_url,
                            params=request_cfg.get("params"),
                            json=request_cfg.get("data") if isinstance(request_cfg.get("data"), dict) else None,
                            data=request_cfg.get("data") if isinstance(request_cfg.get("data"), str) else None,
                            headers=request_cfg.get("headers"),
                        )

                        output_lines.append(f"    Status: {response.status_code}")
                        output_lines.append(f"    Time: {response.elapsed.total_seconds() * 1000:.0f}ms")

                        # 提取变量
                        extract_cfg = step.get("extract", [])
                        for ext in extract_cfg:
                            var_name = ext.get("name")
                            ext_from = ext.get("from", "body")
                            expression = ext.get("expression", "")

                            if ext_from == "body":
                                try:
                                    import jsonpath_ng
                                    body = response.json()
                                    if expression.startswith("$."):
                                        jsonpath_expr = jsonpath_ng.parse(expression)
                                        match = jsonpath_expr.find(body)
                                        if match:
                                            extracted_vars[var_name] = match[0].value
                                            output_lines.append(f"    提取: {var_name} = {match[0].value}")
                                except Exception:
                                    pass

                        # 验证断言
                        validate_cfg = step.get("validate", [])
                        for v in validate_cfg:
                            assert_field = v.get("assert")
                            expect = v.get("expect")

                            if assert_field == "status_code":
                                if response.status_code != expect:
                                    all_success = False
                                    output_lines.append(f"    ✗ 断言失败: status_code={response.status_code}, 期望={expect}")
                                else:
                                    output_lines.append(f"    ✓ 断言通过: status_code={expect}")

                    except Exception as e:
                        all_success = False
                        output_lines.append(f"    ✗ 请求失败: {e}")

            duration_ms = int((time.time() - start_time) * 1000)
            output_lines.append(f"\n执行完成: {'✓ 通过' if all_success else '✗ 失败'} ({duration_ms}ms)")

            return TestResult(
                success=all_success,
                output="\n".join(output_lines),
                duration_ms=duration_ms,
            )

        except Exception as e:
            return TestResult(
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    @app.get("/envs")
    async def get_envs():
        """获取可用环境列表"""
        return {
            "envs": [
                {"name": k, "base_url": v.base_url, "description": v.description or v.name}
                for k, v in ENVIRONMENTS.items()
            ]
        }

    @app.post("/test-endpoint")
    async def test_endpoint(body: dict):
        """测试单个端点"""
        import httpx

        method = body.get("method", "GET")
        url = body.get("url", "")
        data = body.get("data")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start = time.time()
                response = await client.request(method=method, url=url, json=data)
                duration = int((time.time() - start) * 1000)

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time_ms": duration,
                    "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text[:500],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/parse-yaml")
    async def parse_yaml(body: dict):
        """解析 YAML 内容"""
        import yaml
        yaml_content = body.get("yaml_content", body.get("yaml", ""))
        try:
            test_case = yaml.safe_load(yaml_content)
            return {"success": True, "test_case": test_case}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return app


# ─────────────────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=9243)
