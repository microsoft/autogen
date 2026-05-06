FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir -U autogenstudio

EXPOSE 8080

CMD ["autogenstudio", "ui", "--host", "0.0.0.0", "--port", "8080", "--appdir", "/app/data"]
