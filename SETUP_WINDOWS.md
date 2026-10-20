# MülkAnaliz — Windows yerel çalıştırma ve teslim notları

Bu paket yerel bilgisayarda çalıştırılmak üzere hazırlanmıştır. İlk kurulum için Python 3.12+ ve Node.js LTS (npm dahil) gerekir. Yerel kullanımda Docker/PostgreSQL zorunlu değildir.

## Hızlı kurulum

1. ZIP dosyasını kalıcı bir klasöre çıkarın (OneDrive senkronizasyonu sırasında dosya kilidi oluyorsa OneDrive dışı bir klasör tercih edin).
2. `KURULUM.bat` dosyasına çift tıklayın ve tamamlanmasını bekleyin.
3. Sonraki açılışlarda `BASLAT.bat` dosyasına çift tıklayın.
4. Tarayıcıdan `http://localhost:3000` adresini açın.

Yerel demo hesabı: kullanıcı adı `demo`, parola `demo12345678`.

## Veritabanı kalıcılığı

Varsayılan yerel veritabanı `backend/data/real_estate_dev.db` dosyasında tutulur. Yol, terminalin hangi klasörde açıldığından bağımsız olarak backend konumuna göre çözülür. Uygulamayı veya bilgisayarı kapatıp açmak kayıtları silmez. Bu dosyayı silmeyin ve projeyi başka klasöre taşırken veri dosyasını da birlikte taşıyın. Yedek almak için uygulamayı kapatıp bu dosyanın bir kopyasını alın.

Bu varsayılan yerel geliştirme kurulumu için veritabanı türü SQLite'tır. PostgreSQL'e geçiş istenirse `backend/.env` içindeki `DATABASE_URL` ayrıca yapılandırılmalıdır.

## Elle çalıştırma

Backend terminali:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend için ikinci terminal:

```powershell
cd frontend
npm run dev
```

Kontrol adresleri: `http://127.0.0.1:8000/health`, `http://127.0.0.1:8000/ready`, `http://127.0.0.1:8000/docs`.

## Excel raporu

Excel indirme isteği, oturum açma sırasında `sessionStorage` içine kaydedilen erişim token'ını `Authorization: Bearer ...` başlığıyla gönderir. Tarayıcı sekmesi kapatıldığında oturum anahtarı temizlenebilir; bu durumda yeniden giriş yapın. Excel dışa aktarma korumalı bir API işlemidir.

## Testler

Backend klasöründe:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend klasöründe:

```powershell
npm run typecheck
npm run build
```

Demo hesabı yalnızca `ENVIRONMENT=development` iken otomatik hazırlanır. Bu demo bilgilerini internete açık bir dağıtımda kullanmayın.
