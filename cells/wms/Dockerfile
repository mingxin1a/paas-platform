# WMS 细胞 - 独立可运行镜像（解耦：仅 PORT）
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY api_contract.yaml cell_profile.md auto_healing.yaml ./
ENV PORT=8003
EXPOSE 8003
CMD ["python", "-m", "src.app"]
