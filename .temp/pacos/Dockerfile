# PACOS backend (FastAPI + Nemotron core). Local dev / Railway deploy.
FROM python:3.11-slim

WORKDIR /app

# Install the core package + backend deps.
COPY pyproject.toml README.md ./
COPY src ./src
COPY backend ./backend
RUN pip install --no-cache-dir -e . -r backend/requirements.txt

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
