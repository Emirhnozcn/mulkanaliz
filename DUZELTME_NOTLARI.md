# MülkAnaliz düzeltme notları

## Yapılan değişiklikler
- Chrome eklentisi API girişinde e-posta yerine backend'in gerçekten beklediği `username` alanını gönderiyor. Önceki davranış, doğru parola kullanılsa bile HTTP 422 üretebiliyordu.
- Sahibinden ilan detaylarında oda düzeni, bina yaşı, dairenin bulunduğu kat ve bina kat sayısı için daha geniş DOM çıkarımı eklendi.
- Eklenti önizlemesine `Bulunduğu kat` ve `Bina kat sayısı` alanları eklendi.
- `2+1` oda düzeni aktarımda sayısal `room_count=3` olarak kaydediliyor ve orijinal düzen notlarda korunuyor.
- Bina yaşı aralık metni ilk sayısal değeriyle sayısal alana aktarılıyor; orijinal metin notlarda korunuyor.
- API şeması ve aktarım servisi `floor_number` ile `total_floors` alanlarını kabul edip `residential_details` tablosuna kaydediyor.
- Yeni Alembic migration `0005_residential_floors` eklendi.
- HTTP 422 yanıtındaki alan bazlı doğrulama hataları eklenti durum alanında daha okunabilir gösteriliyor.
- İlan detay sayfasında kaynak bağlantısı zaten bulunuyordu (`Kaynak ilanı aç`); yeni kayıtlar için de `source_url` aktarılıyor.
- Giriş token'ı Chrome `storage.local` içinde saklanmaya devam ediyor; eklenti açıldığında yükleniyor. Parola saklanmıyor.

## Doğrulama
- Chrome eklentisi TypeScript build: başarılı.
- Chrome eklentisi TypeScript typecheck: başarılı.
- Frontend Nuxt build: bu Linux çalışma ortamında `nuxt: Permission denied` nedeniyle tamamlanamadı.
- Backend pytest: çalışma ortamında `psycopg` paketi bulunmadığı için testler başlatılamadı. Gerçek PostgreSQL ile entegrasyon testi yapılmış değildir.

## Windows'ta uygulama
1. Backend `.env.example` dosyasını `.env` olarak kopyalayıp kendi PostgreSQL bağlantı bilgilerinizi girin. Gerçek `.env` ve parolalar pakete dahil edilmedi.
2. Backend klasöründe `alembic upgrade head` çalıştırın.
3. Backend'i başlatın: `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
4. `chrome-extension` klasöründe `npm install` ve `npm run build` çalıştırın.
5. Chrome `chrome://extensions` sayfasında geliştirici modunu açıp `chrome-extension` klasörünü yükleyin veya var olan uzantıda Yenile'ye basın.
6. Girişte e-posta değil backend kullanıcı adını kullanın.

Not: Sahibinden sayfasının gerçek DOM'u çalışma ortamında canlı olarak test edilemediğinden, alan çıkarımının her ilan türünde kusursuz olduğu garanti edilemez. Önizleme alanlarını kaydetmeden önce kontrol edin.
