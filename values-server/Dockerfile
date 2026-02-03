FROM python:3.11-slim

WORKDIR /app

COPY values-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY values-server/app.py .
COPY data/values ./data/values

EXPOSE 5002

CMD ["python", "app.py"]