FROM python:3.11-slim

WORKDIR /app

COPY schema-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY schema-server/app.py .
COPY data/schemas ./data/schemas

EXPOSE 5001

CMD ["python", "app.py"]