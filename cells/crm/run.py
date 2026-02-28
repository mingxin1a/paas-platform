#!/usr/bin/env python3
"""CRM 细胞启动入口：FastAPI + Uvicorn。"""
import os
import sys

# 确保 cells/crm 根目录在 path 中
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from src.config import PORT

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=PORT, reload=False)
