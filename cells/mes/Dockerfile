# MES 细胞 - 独立可运行镜像（孵化器交付标准）
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY api_contract.yaml cell_profile.md auto_healing.yaml ./
ENV PORT=8006
EXPOSE 8006
CMD ["python", "-m", "src.app"]
