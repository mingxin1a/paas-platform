# CRM 细胞 - 独立可运行镜像（解耦：仅 PORT，不依赖 PaaS）
# 构建上下文须为本目录：cells/crm
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY run.py ./
COPY api_contract.yaml cell_profile.md auto_healing.yaml completion.manifest delivery.package ./
ENV PORT=8001
EXPOSE 8001
CMD ["python", "run.py"]
