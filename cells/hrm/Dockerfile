FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY api_contract.yaml cell_profile.md auto_healing.yaml ./
ENV PORT=8004
EXPOSE 8004
CMD ["python", "src/app.py"]
