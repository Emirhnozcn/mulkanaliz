# MülkAnaliz — Nuxt 4 Frontend

Türkçe, responsive gayrimenkul ilan yönetimi ve fiyat analizi arayüzü. Nuxt 4, Vue 3 ve TypeScript kullanır.

## Kurulum

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Windows PowerShell'de `cp .env.example .env` yerine `Copy-Item .env.example .env` kullanılabilir.

Frontend varsayılan olarak `http://127.0.0.1:8000/api/v1` adresindeki API'ye bağlanır. Farklı ortamda `.env` içindeki `NUXT_PUBLIC_API_BASE` değerini değiştirin. Bu değişken yalnızca API URL'si içindir; API anahtarı veya parola koymayın.

## Backend bağlantısı

Backend'i kendi talimatlarına göre başlatın. `backend/.env.example` içinde `CORS_ORIGINS=http://localhost:3000` ayarı vardır. FastAPI CORS middleware'i bu ayarı kullanır. Frontend'i başka bir origin üzerinden sunuyorsanız backend `CORS_ORIGINS` değerine o origin'i ekleyin.

## Sayfalar

- `/login` — backend oturum açma ve çalışan kaydı akışı.
- `/` — dashboard; fiyat özeti, fiyat dağılımı, gayrimenkul türü karşılaştırması ve son ilanlar.
- `/listings` — API üzerinden filtrelenebilir, sıralanabilir, sayfalanabilir ilan listesi.
- `/listings/new` — mevcut gayrimenkul ID'sine ilan kaydı ekleme.
- `/listings/:id` — ilan detayları ve fiyat gözlemleri.
- `/listings/:id/edit` — ilan güncelleme.
- `/price-history`, `/listings/:id/price-history` — fiyat geçmişi.
- `/analytics/neighborhoods` — mahalle bazlı karşılaştırma.
- `/filters` — konut/a arazi türüne göre gelişmiş filtreler ve analiz.
- `/filters/saved` — bu tarayıcıda saklanan filtreler.
- `/users` — kullanıcı listeleme.
- `/export` — oturum token'ı ile korumalı API'den CSV/Excel dışa aktarma.

## Veri güvenliği ve doğruluk

- Analiz, ilan ve kullanıcı verileri canlı API yanıtlarından alınır; API hatasında sahte veri gösterilmez.
- API erişim hataları, yükleniyor ve boş sonuç durumları ayrı gösterilir.
- Oturum erişim token'ı sekme oturumu boyunca `sessionStorage` içinde tutulur ve korumalı API isteklerine Bearer başlığı olarak eklenir.
- Backend iş API'leri oturum doğrulaması gerektirir; yönetim işlemleri rol bazlı yetkilendirilir.
- Backend'de gayrimenkul oluşturma/detay endpoint'leri olmadığından yeni ilan formu mevcut `property_id` bekler.
- Kayıtlı filtreler şu anda hesaplar arası senkronize edilmez; tarayıcı `localStorage` alanında tutulur.
- CSV tarayıcıda önizlemede getirilen kayıtlar üzerinden; Excel ise korumalı backend endpoint'i üzerinden indirilir (Excel için en fazla 500 kayıt).

## Kontroller

```bash
npm run build
npm run typecheck
```

Kurulum ortamında npm paketleri indirilemezse derleme kontrolü çalıştırılamaz; bu durum derlemenin başarılı olduğu anlamına gelmez.
