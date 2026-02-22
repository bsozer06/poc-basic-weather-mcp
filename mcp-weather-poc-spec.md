# Specification: MCP Weather Service (PoC)

## 1. Overview

Bu proje, bir LLM'in (istemci) yerel bir Python betiği (sunucu) üzerinden gerçek zamanlı hava durumu verilerine erişmesini sağlayan bir Model Context Protocol (MCP) uygulamasıdır.

### Core Concept

Model, hava durumunu "tahmin etmez" veya eğitim verisinden kullanmaz. Bunun yerine, bu spekte tanımlanan Tool'u çağırarak dış dünyaya güvenli bir köprü kurar.

## 2. Interface Specification (The Contract)

MCP standardına göre, sunucumuz aşağıdaki yetenekleri (capabilities) dışarıya açmalıdır:

### 2.1 Tool Definition: `get_weather`

LLM'in çağırabileceği fonksiyonun teknik speği:

- **Name:** `get_weather`
- **Description:** Belirtilen şehir için güncel hava durumu ve sıcaklık bilgisini döner.
- **Input Schema (JSON):**

```json
{
  "type": "object",
  "properties": {
    "city": {
      "type": "string",
      "description": "Hava durumu sorgulanacak şehrin adı (örn: Istanbul)"
    },
    "unit": {
      "type": "string",
      "enum": ["celsius", "fahrenheit"],
      "default": "celsius"
    }
  },
  "required": ["city"]
}
```

## 3. Data Integrity & Validation

Spec-Driven Design gereği, çıktı sadece metin değil, bir şema uyumlu olmalıdır:

| Field       | Type    | Constraint                        |
|-------------|---------|-----------------------------------|
| temperature | float   | Gerçek sayı                       |
| condition   | enum    | `Sunny`, `Cloudy`, `Rainy`, `Snowy` |
| timestamp   | ISO8601 | `YYYY-MM-DDTHH:mm:ssZ`            |

## 4. Operational Requirements (PoC Steps)

Bir bilgisayar bilimci gözüyle sistemin çalışma akışı:

- **Transport Layer:** Sunucu ve İstemci `stdio` (standart giriş/çıkış) üzerinden haberleşir.
- **Handshake:** İstemci bağlandığında sunucu `list_tools` komutuna yukarıdaki JSON şemasıyla yanıt verir.
- **Execution:**
  1. Kullanıcı: *"İstanbul'da hava nasıl?"* der.
  2. LLM: Spekteki şemaya uygun olarak `get_weather(city="Istanbul")` çağrısını oluşturur.
  3. MCP Server: İsteği alır, işlemi yapar ve JSON yanıt döner.

## 5. Success Metrics (The "Spec" Test)

PoC'nin başarılı sayılması için aşağıdaki testlerden geçmesi gerekir:

- [ ] **Schema Validation:** Sunucu, geçersiz bir şehir formatında hata (error code) dönüyor mu?
- [ ] **Type Safety:** Sıcaklık değeri her zaman `float` mı geliyor?
- [ ] **Zero-Hallucination:** LLM, bilmediği bir şehir için araç çağrısı yapmadan "uyduruyor" mu? (Hedef: Hayır).