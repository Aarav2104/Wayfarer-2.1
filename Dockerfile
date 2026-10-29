# Generic container (Render, Fly.io, Cloud Run, Hugging Face Docker Spaces, your own server)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY frontend frontend
WORKDIR /app/backend
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
