#!/usr/bin/env python3
"""启动数据湖服务：多 Cell 汇聚、元数据/血缘/质量/敏感、权限、报表与导出。"""
import os
import sys

sys.path.insert(0, os.environ.get("APP_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from platform_core.data_lake.app import create_app

app = create_app()
port = int(os.environ.get("DATALAKE_PORT", "8006"))
app.run(host="0.0.0.0", port=port)
