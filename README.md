# MülkAnaliz — Gayrimenkul Analiz Uygulaması

Bu paket, yüklediğiniz proje kaynakları temizlenerek hazırlanmıştır. Yerel `.env`, sanal ortamlar, Node bağımlılıkları, derleme çıktıları ve geçici dosyalar pakete dahil edilmemiştir.

## Teknoloji
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- Frontend: Nuxt 4, Vue 3, TypeScript
- Rapor dışa aktarma: CSV ve Excel (`.xlsx`)

## Geliştirme ortamını başlatma

### 1. PostgreSQL
Docker Desktop kurulu ve çalışır durumda olmalı. `backend` klasöründe:

```powershell
docker compose -f docker-compose.dev.yml up -d
```

Compose dosyasındaki port/bağlantı ayarlarını kontrol edin. Sonra `.env.example` dosyasını `.env` olarak kopyalayıp kendi yerel ayarlarınızı girin.

### 2. Backend
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

API varsayılan olarak `http://127.0.0.1:8000` adresinde çalışır; dokümantasyon `/docs` yolundadır (ayarlarla kapatılmadıysa).

### 3. Frontend
Yeni bir terminalde:

```powershell
cd frontend
npm install
$env:NUXT_PUBLIC_API_BASE="http://127.0.0.1:8000/api/v1"
npm run dev
```

Nuxt geliştirme adresi terminalde gösterilir.

## Excel ve CSV raporu
Raporlama sayfasındaki CSV düğmesi ekrandaki önizleme kayıtlarını dışa aktarır. Excel düğmesi backend'in `/api/v1/exports/listings.xlsx` uç noktasından en fazla 500 ilanı `.xlsx` biçiminde indirir. Bu Excel uç noktası mevcut backend rapor sorgusunu kullanır; sayfadaki filtreler Excel indirmesine uygulanmaz.

## Doğrulama notu
Bu ZIP, yüklediğiniz kaynaklardan yeniden paketlendi ve Excel indirme düğmesi eklendi. Bu çalışma ortamında Docker/PostgreSQL servisi ve Node bağımlılıklarıyla uçtan uca uygulama testi yapılamadı. Dolayısıyla bunu canlı veritabanında tamamen doğrulanmış bir üretim sürümü olarak değerlendirmeyin; ilk çalıştırmada kurulum adımlarını izleyip test edin.


## Son geliştirme notları (dinamik ilan oluşturma)
- Web'deki yeni ilan formu artık kullanıcı ID'si veya gayrimenkul ID'si istemez.
- `/api/v1/listings/quick-create`, oturumdaki kullanıcıyı kullanarak gayrimenkul ve ilk ilan kaydını aynı işlemde oluşturur.
- Konum oluşturma endpoint'i oturum açmış kullanıcıya açıktır; aynı üst konum altında aynı normalize edilmiş ad tekrar gelirse mevcut konumu döndürür.
- Şehir listesi veritabanındaki `locations` tablosunda `level=province` kayıtları olarak tutulur. Yeni kurulumda şehirleri yönetici/seed verisiyle eklemek gerekir; bu paket otomatik olarak 81 ili seed etmez.
- Hızlı kayıt endpoint'i şu an temel gayrimenkul + ilan + ilk fiyat geçmişini oluşturur. Net/brüt m² ve oda/bina yaşı gibi detay alanlarının kaydı için ayrıca detay formu/API desteği gerekir.


## Çalışan girişi

Kurulum, test hesabı ve kayıt kodu için `AUTH-AND-TEST-ACCOUNT.md` dosyasına bakın.

## Son gözden geçirme

Kontrol sonuçları ve doğrulanamayan akışlar için `FINAL-REVIEW-REPORT.md` dosyasını okuyun. Backend ve eklenti kontrolleri başarılıdır; PostgreSQL entegrasyonu ve Nuxt production build bu ortamda doğrulanmamıştır.


## Python sürümü

Kurulum betiği Python 3.12.x kullanır. Windows'ta Python 3.12 (64-bit) kurulu olmalıdır.
