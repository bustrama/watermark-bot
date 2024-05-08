# Build stage
FROM python:3.10-slim

WORKDIR /app
COPY main.py .
COPY requirements.txt .
COPY .env .

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
