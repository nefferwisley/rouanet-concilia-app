# Build a partir da RAIZ do repo (não da pasta backend/), porque este
# Dockerfile precisa copiar o pacote motor/ que é irmão de backend/:
#   docker build -f backend/Dockerfile -t rouanet-api .
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY motor/ ./motor/
COPY db/ ./db/
ENV PYTHONPATH=/app
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
