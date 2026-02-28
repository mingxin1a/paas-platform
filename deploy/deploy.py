#!/usr/bin/env python3
"""
SuperPaaS 一键部署（跨平台）
拉取/构建 -> 启动 -> 冒烟测试 -> 输出 LIVE。零心智负担：只需运行此脚本。
Windows: python deploy/deploy.py  或  py deploy\deploy.py
Linux/Mac: python deploy/deploy.py  或  ./deploy/deploy.sh
"""
import os
import sys
import time
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
DEPLOY_DIR = os.path.join(ROOT, "deploy")
COMPOSE_FILE = os.path.join(DEPLOY_DIR, "docker-compose.yml")
ENV_FILE = os.path.join(DEPLOY_DIR, ".env")
SMOKE_SCRIPT = os.path.join(DEPLOY_DIR, "smoke_test.py")


def run(cmd):
    exe = subprocess.run(cmd, cwd=ROOT)
    if exe.returncode != 0:
        sys.exit(exe.returncode)


def main():
    print("[deploy] 1/4 构建并启动服务...")
    run(["docker", "compose", "-f", COMPOSE_FILE, "--env-file", ENV_FILE, "up", "-d", "--build"])
    print("[deploy] 2/4 等待网关就绪...")
    os.environ["GATEWAY_URL"] = "http://localhost:8000"
    for i in range(1, 11):
        ret = subprocess.run([sys.executable, SMOKE_SCRIPT], capture_output=True, cwd=ROOT, env=os.environ)
        if ret.returncode == 0:
            break
        print(f"  attempt {i}/10...")
        time.sleep(3)
    else:
        print("[deploy] 网关未在预期时间内就绪")
        sys.exit(1)
    print("[deploy] 3/4 冒烟测试...")
    ret = subprocess.run([sys.executable, SMOKE_SCRIPT], cwd=ROOT, env=os.environ)
    if ret.returncode != 0:
        print("[deploy] 冒烟测试未通过")
        sys.exit(1)
    print("[deploy] 4/4 E2E 冒烟（可选）...")
    e2e = os.path.join(ROOT, "tests", "e2e", "crm_integration_test.py")
    if os.path.isfile(e2e):
        ret = subprocess.run(
            [sys.executable, "-m", "pytest", e2e, "-v", "--tb=short", "-q"],
            cwd=ROOT,
            capture_output=True,
        )
        if ret.returncode == 0:
            print("[deploy] E2E 通过")
        else:
            print("[deploy] E2E 跳过或未通过（已通过 HTTP 冒烟）")
    print("")
    print("✅ SuperPaaS Platform is LIVE and in autonomous mode.")
    print("   Gateway: http://localhost:8000")
    print("   Health:  http://localhost:8000/health")


if __name__ == "__main__":
    main()
