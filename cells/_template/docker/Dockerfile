# 细胞通用 Dockerfile：复制模板后仅改 WORKDIR/COPY 与端口
FROM python:3.11-slim
WORKDIR /app
# 复制依赖与代码（复制模板后改为当前细胞目录结构）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY config/ ./config/
COPY models/ ./models/
COPY service/ ./service/
COPY api/ ./api/
COPY main.py ./
ENV PORT=8001
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
