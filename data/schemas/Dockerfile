FROM python:3.11-slim

WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY app.py .

# Port 5001'i aç
EXPOSE 5001

# Uygulamayı başlat
CMD ["python", "app.py"]
```

---

**ŞUAN `schema-server` KLASÖRÜ ŞÖYLE OLMALI:**
```
schema-server/
├── app.py
├── requirements.txt
└── Dockerfile