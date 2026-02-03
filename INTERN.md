# INTERN.md - Nurşen Akay

## Proje Özeti

Bu proje, kullanıcıların **doğal dil** kullanarak uygulama konfigürasyonlarını güncellemesini sağlayan **AI destekli bir sistem**dir. Sistem, JSON şemalarını ve değerleri yöneten 3 mikroservis ve bir AI modeli kullanır.

---

## Mimari Kararlar

### 1. Mikroservis Mimarisi

**Neden 3 ayrı servis?**
- **Separation of Concerns**: Her servis tek bir işten sorumlu
- **Ölçeklenebilirlik**: Servisleri bağımsız olarak ölçeklendirilebilir
- **Bakım kolaylığı**: Bir serviste sorun olduğunda diğerleri etkilenmez
┌─────────────┐
│  Kullanıcı  │
└──────┬──────┘
│
▼
┌──────────────────┐
│   Bot Service    │ (5003)
│   (AI-powered)   │
└────┬────────┬────┘
│        │
▼        ▼
┌─────────┐ ┌─────────┐
│ Schema  │ │ Values  │
│ Service │ │ Service │
│ (5001)  │ │ (5002)  │
└─────────┘ └─────────┘
---

### 2. AI Model Seçimi: Llama 3.2 (3B)

**Neden Llama 3.2:3b?**

✅ **Avantajlar:**
- **Hafif**: 3 milyar parametre - lokal makinelerde hızlı çalışır
- **JSON desteği**: Structured output için optimize edilmiş
- **Hızlı inference**: ~2-3 saniyede yanıt verir
- **Ollama desteği**: Kolay kurulum ve kullanım

❌ **Alternatifler ve neden seçilmedi:**
- **Llama 3.1 (8B/70B)**: Çok ağır, local ortamda yavaş
- **Mistral**: JSON formatında tutarsız yanıtlar
- **Gemma**: Konfigürasyon güncellemelerinde daha az tutarlı

---

### 3. İki Aşamalı AI Süreci

**Neden iki ayrı AI çağrısı?**

1. **İlk çağrı**: Uygulama adını tespit et
   - Girdi: Sadece kullanıcı mesajı
   - Çıktı: `{"app_name": "chat"}`
   - **Neden ayrı?** Schema ve values çok büyük (100KB+), gereksiz yere token harcamayı önler

2. **İkinci çağrı**: Değerleri güncelle
   - Girdi: Kullanıcı mesajı + Schema + Mevcut değerler
   - Çıktı: Güncellenmiş JSON
   - **Neden ayrı?** AI sadece gerekli uygulama için schema yükler, daha hızlı ve doğru

---

### 4. Prompt Engineering Stratejisi

**JSON formatını garanti altına almak için:**
```python
prompt = """
Respond ONLY with a JSON object in this exact format:
{"app_name": "identified_app_name"}
"""
```

**Neden önemli?**
- AI'lar bazen açıklama ekler: "Sure, here is the JSON..."
- Strict format sayesinde `json.loads()` başarılı olur
- Hata yönetimi için fallback mekanizması var

---

### 5. Hata Yönetimi ve Fallback

**AI başarısız olursa ne olur?**
```python
# Fallback: Basit anahtar kelime eşleştirme
if "tournament" in user_input.lower():
    return "tournament"
`**Neden gerekli?**
- AI modelleri %100 garantili değil
- Network sorunları olabilir
- Basit istekler için AI gereksiz

---

## Sistem Akışı (End-to-End)

### Örnek: "set tournament service memory to 1024mb"
```
1. Kullanıcı → Bot Service (POST /message)
   Input: {"input": "set tournament service memory to 1024mb"}

2. Bot Service → Ollama AI
   "Hangi uygulama?"
   ← "tournament"

3. Bot Service → Schema Service (GET /tournament)
   ← tournament.schema.json (68KB)

4. Bot Service → Values Service (GET /tournament)
   ← tournament.value.json (5KB)

5. Bot Service → Ollama AI
   "Schema + mevcut values + kullanıcı isteği"
   ← Güncellenmiş JSON (memory: 1024)

6. Bot Service → Kullanıcı
   ← Güncellenmiş tournament.value.json
```

**Toplam süre**: ~5-8 saniye

---

## Teknik Detaylar

### Docker Compose Yapılandırması

**Neden depends_on + healthcheck?**
```yaml
bot-service:
  depends_on:
    ollama:
      condition: service_healthy
```
- Bot service, Ollama hazır olmadan başlamaz
- Model indirme süresi (~2-3 dakika) beklenir
- Servisler arası bağımlılık garantilenir

**Neden volume mount?**
```yaml
volumes:
  - ./data/schemas:/data/schemas:ro
```
- `:ro` = read-only, servis dosyaları değiştiremez
- Güvenlik: Yanlışlıkla şema silinmesini önler
- Hot-reload: Dosya değişiklikleri anında yansır

---

## Karşılaşılan Zorluklar ve Çözümler

### 1. Ollama Model İndirme

**Sorun**: Container başladığında model yok
```bash
Error: model 'llama3.2:3b' not found
```

**Çözüm**: Entrypoint script ile otomatik indirme
```yaml
command:
  - |
    /bin/ollama serve &
    sleep 10
    ollama pull llama3.2:3b
```

---

### 2. AI Yanıtlarında Tutarsızlık

**Sorun**: AI bazen şu formatı veriyor:
```
"Sure! Here's the updated JSON: {...}"
```

**Çözüm**: 
- Prompta "ONLY JSON" vurgusu
- `json.loads()` ile parse deneme
- Fallback mekanizması

---

### 3. Birim Dönüşümleri

**Sorun**: Kullanıcı "1024mb" diyor, schema "MiB" istiyor

**Çözüm**: AI'a kuralları açıkça belirt
```
- For memory: use MiB (mebibytes) as integer
- "1024mb" → 1024
- "80%" → calculate as milliCPU or ratio
```

---

## Test Senaryoları

### Test 1: Memory Güncellemesi
```bash
curl -X POST http://localhost:5003/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set tournament service memory to 1024mb"}'
```

**Beklenen**: `limitMiB: 1024`

---

### Test 2: Environment Variable
```bash
curl -X POST http://localhost:5003/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set GAME_NAME env to toyblast for matchmaking service"}'
```

**Beklenen**: `envs: {"GAME_NAME": "toyblast"}`

---

### Test 3: CPU Limit (Yüzde)
```bash
curl -X POST http://localhost:5003/message \
  -H "Content-Type: application/json" \
  -d '{"input": "lower cpu limit of chat service to 80%"}'
```

**Beklenen**: `limitMilliCPU: 1200` (1500'ün %80'i)

---

## Gelecek İyileştirmeler

1. **Schema Validation**: JSON Schema ile response validation
2. **Caching**: Tekrarlayan istekler için Redis cache
3. **Monitoring**: Prometheus + Grafana ile metrik toplama
4. **Rate Limiting**: API abuse'i önlemek için
5. **Authentication**: API key bazlı auth sistemi

---

## Kurulum ve Çalıştırma

### Gereksinimler
- Docker & Docker Compose
- En az 8GB RAM (Ollama için)
- 5GB disk alanı (model için)

### Başlatma
```bash
docker compose up --build
```

**İlk başlatma**: ~5 dakika (model indirme)
**Sonraki başlatmalar**: ~30 saniye

---

## Sonuç

Bu proje, **AI ve mikroservis mimarisini** birleştirerek karmaşık JSON konfigürasyonlarını **basit doğal dil** ile yönetmeyi sağlıyor. Llama 3.2 modeli sayesinde local ve hızlı çalışan, Docker Compose ile kolayca deploy edilebilen bir sistem oluşturduk.

**Öğrendiklerim**:
- LLM prompt engineering
- Mikroservis arası iletişim
- Docker Compose orchestration
- JSON Schema validation

---

**Proje Sahibi**: Nurşen Akay  

```

**Kaydet:** `Cmd + S`

---

## 🎯 **ADIM 7: SON KONTROL**

Şu an proje yapısı şöyle olmalı:
```
intern-homework-master/
├── bot-server/
│   ├── app.py              ✅
│   ├── Dockerfile          ✅
│   └── requirements.txt    ✅
├── data/
│   ├── schemas/           ✅ (zaten vardı)
│   └── values/            ✅ (zaten vardı)
├── schema-server/
│   ├── app.py              ✅
│   ├── Dockerfile          ✅
│   └── requirements.txt    ✅
├── values-server/
│   ├── app.py              ✅
│   ├── Dockerfile          ✅
│   └── requirements.txt    ✅
├── docker-compose.yml      ✅
├── INTERN.md               ✅
└── README.md               ✅ (zaten vardı)

