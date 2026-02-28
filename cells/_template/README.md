# 细胞模块通用模板

符合**细胞化架构规范**与**《接口设计说明书》**，内置健康检查、鉴权、统一响应与错误码。新增 ERP、MES 等模块时，复制本目录后仅需填充业务逻辑即可接入。

- **目录结构**：api（接口）、models（数据模型）、service（业务逻辑）、config（配置）、tests（测试）、docker（部署）
- **使用说明**：见 [模板使用说明.md](模板使用说明.md)
- **运行**：`pip install -r requirements.txt` 后 `uvicorn main:app --host 0.0.0.0 --port 8001`
- **交付校验**：`sh verify_delivery.sh`（Windows 可用 Git Bash 或 WSL）
