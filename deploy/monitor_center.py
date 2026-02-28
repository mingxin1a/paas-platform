#!/usr/bin/env python3
"""
PaaS 监控中心（最小实现）
接收细胞 ai_agent 注册，下发自愈指令；《01_核心法律》管家式 AI 与平台协同。
"""
import os
import json
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# 注册表: cell -> [{"agent_id", "last_heartbeat"}]
_agents = defaultdict(list)
# 指令队列: cell -> [{"action", "params", "id"}]
_instructions = defaultdict(list)


@app.route("/health")
def health():
    return jsonify({"status": "up", "service": "monitor_center"}), 200


@app.route("/register", methods=["POST"])
def register():
    """ai_agent 启动时注册，便于平台下发指令。"""
    body = request.get_json() or {}
    cell = body.get("cell", "crm")
    agent_id = body.get("agent_id", os.environ.get("HOSTNAME", "local"))
    _agents[cell].append({"agent_id": agent_id, "last_heartbeat": None})
    return jsonify({"ok": True, "cell": cell, "agent_id": agent_id}), 200


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    """ai_agent 周期性上报。"""
    body = request.get_json() or {}
    cell = body.get("cell", "crm")
    agent_id = body.get("agent_id", "")
    for a in _agents.get(cell, []):
        if a.get("agent_id") == agent_id:
            import time
            a["last_heartbeat"] = time.time()
            break
    return jsonify({"ok": True}), 200


@app.route("/instructions", methods=["GET"])
def get_instructions():
    """ai_agent 轮询获取待执行指令（如执行自愈）。"""
    cell = request.args.get("cell", "crm")
    agent_id = request.args.get("agent_id", "")
    pending = _instructions.get(cell, [])
    _instructions[cell] = []
    return jsonify({"instructions": pending}), 200


@app.route("/instructions", methods=["POST"])
def push_instruction():
    """平台或人工下发指令（如触发自愈）。"""
    body = request.get_json() or {}
    cell = body.get("cell", "crm")
    action = body.get("action", "log")
    _instructions[cell].append({"id": body.get("id", ""), "action": action, "params": body.get("params", {})})
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9000"))
    app.run(host="0.0.0.0", port=port)
