# MülkAnaliz — Düzeltmeler ve test raporu

## Bu pakette yapılan düzeltmeler
- Yerel demo hesabı hazırlama fonksiyonundaki hatalı `@asynccontextmanager` dekoratörü kaldırıldı. Önceki haliyle fonksiyon çağrıldığında hesabı hazırlama gövdesi çalışmıyordu.
- Yeni yerel veritabanında il seçicisinin boş kalmaması için 81 il başlangıç verisi, geliştirme başlangıcında idempotent olarak eklenir. İlçe ve mahalleler kullanıcı tarafından eklenebilir.
- Yeni ilan formuna **Satılık / Kiralık (aylık)** seçimi eklendi; seçilen `transaction_type` backend'e gönderilir. Fiyat etiketi işlem türüne göre değişir.
- İlan listeleme API'sine `transaction_type=sale|rent` filtresi eklendi.
- Yeni Windows kurulum rehberi ve doğru PostgreSQL bağlantı bilgilerini içeren `.env.example` eklendi.
- İlan türüne göre listeleme filtresi için regresyon testi eklendi.
- İlan formundaki isim normalizasyonu regex'i düzeltildi.

## Otomatik testler
Komut: `python -m pytest -q` (backend)

Sonuç: **54 passed, 2 skipped**.
İki test, `TEST_POSTGRES_URL` verilmediği için PostgreSQL entegrasyon testi olarak atlandı. Testler SQLite tabanlı izole test veritabanıyla geçti.

## Doğrulanamayanlar / teslim öncesi notlar
- Bu çalışma ortamında `npm ci` zaman aşımına uğradı; bu nedenle Nuxt `typecheck` ve production `build` doğrulanamadı.
- Gerçek PostgreSQL entegrasyon testleri çalıştırılmadı; Docker/PostgreSQL erişimi bu test koşusunda doğrulanmadı.
- Değerleme gerçek gerçekleşmiş satış verisi veya resmî ekspertiz değildir; kayıtlı aktif ilan fiyatlarından yaklaşık emsal hesabıdır. Veri yoksa yapay fiyat üretmez.
- Harici ilan sitelerinden veri çekme, sitenin kullanım koşulları ve izinleri kapsamında ayrıca doğrulanmalıdır.

## Başlatma
Windows adımları için `SETUP_WINDOWS.md` dosyasını izleyin. Backend'i başlatmadan önce `.env.example` dosyasını `.env` olarak kopyalayın ve Alembic migration'larını çalıştırın.
