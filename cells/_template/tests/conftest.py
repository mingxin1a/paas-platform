# 测试入口：将细胞根目录加入 path，便于导入 config、api、service、models
from __future__ import annotations

import os
import sys
from pathlib import Path

CELL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CELL_ROOT))
os.chdir(CELL_ROOT)
