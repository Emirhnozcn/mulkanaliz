# MülkAnaliz — Backend

FastAPI + SQLAlchemy 2 + Alembic tabanlı API. Yerel teslim/deneme kurulumunda SQLite kullanılır; PostgreSQL desteği korunmuştur.

## Gereksinimler

- Python 3.12.x (önerilen ve kurulum betiği tarafından kullanılan sürüm)

## Yerel kurulum

Proje kök dizinindeki `KURULUM.bat` ilk kurulum ve bağımlılıkları yükler. Sonraki çalıştırmalarda `BASLAT.bat` kullanılabilir. Elle kurulum için:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Varsayılan veritabanı `backend/data/real_estate_dev.db` dosyasında kalıcıdır. Yol, terminalin geçerli dizinine bağlı değildir; uygulamayı kapatıp açmak kayıtları silmez. Yerel geliştirme hesabı: `demo` / `demo12345678`. Bu hesap yalnızca development ortamında hazırlanır.

İsteğe bağlı PostgreSQL kullanımı için `backend/.env` içinde `DATABASE_URL` ayarlanmalıdır. Gerçek/üretim ortamında demo parolasını ve tüm varsayılan sırları değiştirmeden kullanmayın.

## Veritabanı migration'ları

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Kontrol: `http://127.0.0.1:8000/health`, `http://127.0.0.1:8000/ready`, `http://127.0.0.1:8000/docs`.

## Listing API

Base path: `/api/v1/listings`

- `POST /` — create a listing and its initial asking-price history snapshot (`201`).
- `GET /{listing_id}` — listing details (`404` if missing).
- `GET /` — filtered, sorted list using `limit` (1–500) and `offset` pagination.
- `PATCH /{listing_id}` — partial update; asking-price/currency changes append price history.
- `DELETE /{listing_id}` — soft archive (`204`); archived listings are hidden from lists by default.
- `GET /{listing_id}/price-history` — asking-price history.

Supported list filters include `status`, `property_id`, `property_type` (type code), `province_id`, `district_id`, `neighborhood_id`, `min_price`/`max_price`, `source_name`, and `include_archived`. Residential area filters are explicitly separate: `min_net_area_m2`/`max_net_area_m2` and `min_gross_area_m2`/`max_gross_area_m2`. Land/farmland use `min_parcel_area_m2`/`max_parcel_area_m2`. `min_room_count`/`max_room_count` and `min_building_age`/`max_building_age` only query residential details. `zoning_status` and `zoning_use` query zoned-land details. Multiple filters are combined with AND, while parcel area checks either land or farmland parcel area.

Sorting is restricted to `sort_by=created_at|updated_at|asking_price|id` and `sort_order=asc|desc`; arbitrary SQL fragments are not accepted. Range bounds must be non-negative (positive for area fields), and a minimum cannot exceed its maximum. Invalid request parameters return `422`, missing records `404`, and conflicts `409`.

## Tests

```bash
pytest -q
```

Tests use an isolated in-memory SQLite database so basic API/ORM tests can run without a PostgreSQL server. Production migration and PostgreSQL-specific constraints must additionally be verified against a real PostgreSQL instance.

## Notes

- Source deduplication uses a partial unique index on `(source_name, source_listing_id)` when both values are supplied. API service validation also returns HTTP 409 for duplicates.
- Listing creation writes the listing and initial price-history record in one transaction. Asking-price/currency updates append history in the same transaction only when price or currency changes.
- `password_hash` is generated only on the backend from the submitted password; clients must never submit a hash. Login uses signed, expiring access tokens, and logout increments `token_version` to revoke the user’s current token family.


## Fiyat analizi API'si

Analiz uç noktaları `/api/v1/analytics` altında yer alır. Yalnızca aktif ve arşivlenmemiş ilanlar dahil edilir; para birimleri varsayılan olarak `TRY` ile sınırlandırılır.

- `GET /api/v1/analytics/price-summary`: ilan sayısı, ortalama/medyan/minimum/maksimum ilan fiyatı, alan türüne göre m² fiyatları, fiyat dağılımı, kaydedilmiş fiyat geçmişindeki gözlenen değişim ve son veri güncelleme zamanı.
- `GET /api/v1/analytics/compare?group_by=...`: `property_type`, `neighborhood`, `room_count`, `building_age`, `area_band`, `zoning_status` veya `zoning_use` ölçütüne göre karşılaştırma. Gayrimenkul türleri arası karşılaştırma dışında `property_type` filtresi zorunludur; oda/bina yaşı konut, imar gruplaması `residential_land` ile sınırlandırılır.

Örnekler:

```http
GET /api/v1/analytics/price-summary?property_type=apartment&area_type=net&province_id=34&minimum_listings=5
GET /api/v1/analytics/price-summary?property_type=residential_land&zoning_status=imarlı&min_parcel_area_m2=300
GET /api/v1/analytics/compare?property_type=apartment&group_by=neighborhood&area_type=gross
GET /api/v1/analytics/compare?property_type=residential_land&group_by=zoning_status
```

`area_type=net|gross` yalnızca konut alanı metriğini seçer; imarlı arsa ve tarla için daima `parcel` alanı kullanılır. Yanıttaki `area_price_metrics[].area_type` gerçek kullanılan ölçüyü bildirir. Karışık türde özet istendiğinde m² metrikleri ayrı ölçü türleri halinde döner; karşılaştırma satırında birden fazla ölçü türü varsa tek bir m² değeri üretilmez.

Fiyat dağılımı varsayılan olarak beş eşit genişlikli aralığa bölünür (`bucket_count` ile 1–20 arasında ayarlanabilir). `minimum_listings` varsayılan 5'tir ve yalnızca yorumlama uyarısını değiştirir; istatistiksel güvence sağlamaz. Ortalama ve medyan ayrı sunulur; uç fiyatlar ortalamayı etkileyebileceğinden ikisi birlikte değerlendirilmelidir.

Fiyat geçmişi ölçümü yalnızca sistemde kaydedilmiş en erken ve en geç fiyat gözlemlerini karşılaştırır. İlk kaydedilmiş değer gerçek ilk yayın fiyatı olarak kabul edilmez. Hiçbir ilan fiyatı gerçekleşmiş satış fiyatı gibi sunulmaz; gerçekleşmiş işlemler ayrı `SaleTransaction` modelindedir.

### Test verisi

`tests/test_analytics.py` kontrollü ve yapay **demo** ilanlar oluşturur; örneğin ortalama, medyan, alan fiyatı, uç değer etkisi, arsa/tarla alan ayrımı ve gözlenen fiyat değişimi matematiksel beklentilerle doğrulanır. Bu demo kayıtları üretim verisi değildir ve veritabanına kalıcı bir seed olarak eklenmez.

## İzinli kaynaklardan tek ilan içe aktarma

`POST /api/v1/imports/listing` endpoint'i, danışmanın kaynak sayfasında gördüğü verileri kontrol edip onayladıktan sonra tek bir ilanı içe aktarmak içindir. Zorunlu alanlar: `source_url`, `source_name`, `created_by`, `location_id`, `property_type_code`, `asking_price`. `source_listing_id` mümkünse kaynakta görünen sabit kimlik olmalıdır. Desteklenen tür kodları: `apartment`, `detached_house`, `villa`, `residential_zoned_land`, `commercial_zoned_land`, `farmland`. Tür kodlarının `property_types` tablosunda seed edilmiş olması gerekir.

- İlk aktarım yeni gayrimenkul + ilan + başlangıç fiyat gözlemi oluşturur (`201`).
- Aynı kaynak ve harici kimlik (veya aynı kaynak URL'si) yeniden gelirse kopya oluşturmaz (`200`). Fiyat/para birimi değişmişse mevcut fiyat geçmişine `price_changed` kaydı ekler; aynı fiyat için yeni fiyat geçmişi satırı oluşturmaz.
- Konut alanları (`net_area_m2`, `gross_area_m2`, `room_count`, `building_age`) ile arsa/tarla alanı (`parcel_area_m2`) birbirine karıştırılmaz. Arsa/tarla için parsel alanı zorunludur.
- Konum ve danışman ID'si mevcut kayıtları işaret etmelidir. Eksik veriler `null` bırakılabilir; değer uydurulmaz.

### Chrome eklentisi

`../chrome-extension/` klasöründe Manifest V3 + TypeScript eklentisi bulunur. Kurulum ve CORS talimatları klasörün README dosyasındadır. Eklenti yalnızca kullanıcı eylemiyle açık sekmeyi okur ve önizleme sonrası aktarır; arka plan taraması yapmaz. Platform bazında şartlar ve veri kullanım hakları değerlendirilmeden herhangi bir siteye özel adaptör eklenmemelidir. Eklenti gerçek kullanıcı oturumuyla birlikte kullanılmalı; API üzerindeki token doğrulaması ve rol/sahiplik kontrolleri frontend davranışından bağımsızdır.

## Güvenlik regresyon testleri ve PostgreSQL entegrasyonu

Varsayılan test paketi SQLite bellek içi veritabanında çalışır:

```bash
DATABASE_URL='sqlite+pysqlite:///:memory:' python -m pytest -q
```

Gerçek PostgreSQL entegrasyon testi isteğe bağlıdır ve **yalnızca boş, atılabilir bir test veritabanında** çalıştırılır. Veritabanı adının `_test` veya `_testing` ile bitmesi gerekir; fixture temiz migration uyguladıktan sonra test sonunda tabloları kaldırır. Üretim veya paylaşılan veritabanını kesinlikle bu değişkene vermeyin.

```bash
# Örnek URL; kullanıcı/parola değerlerini terminal geçmişine veya repoya yazmayın.
export TEST_POSTGRES_URL='postgresql+psycopg://test_user:...@localhost:5432/rea_test'
python -m pytest -q tests/test_postgres_integration.py
```

PostgreSQL sürücüsü (`psycopg[binary]`) ve çalışan PostgreSQL sunucusu gerekir. `TEST_POSTGRES_URL` tanımlı değilse entegrasyon testi açıkça `SKIPPED` olur; bu sonuç PostgreSQL testinin başarılı olduğu anlamına gelmez.

Token logout işlemi kullanıcının `token_version` değerini artırır ve bu kullanıcı için verilmiş tüm erişim tokenlarını geçersiz kılar. Mevcut oturumların tamamını kapatmak kasıtlı davranıştır. Migration uygulayın:

```bash
alembic upgrade head
```

## PostgreSQL entegrasyon testi (Aşama 3.1)

PostgreSQL testleri SQLite testlerinden ayrı çalışır. `docker-compose.test.yml` yalnızca atılabilir bir PostgreSQL 16 test servisi başlatır; verisi container içi `tmpfs` üzerindedir ve port yalnızca `127.0.0.1:55432` adresine bağlanır. Bu compose dosyası üretim dağıtımı değildir.

Gereksinimler: Docker Engine + Compose v2, Python bağımlılıkları (özellikle `psycopg[binary]`) ve boş bir test veritabanı. Backend klasöründe:

```bash
# Test hizmetini başlat ve sağlıklı olmasını bekle
 docker compose -f docker-compose.test.yml up -d --wait postgres-test

# Ayrı bir test ortamını açıkça seç; bu değerler sadece bu geçici test servisi içindir.
export ENVIRONMENT=test
export DATABASE_URL='sqlite+pysqlite:///:memory:'
export TEST_POSTGRES_URL='postgresql+psycopg://rea_test_user:rea_test_only_password@127.0.0.1:55432/rea_test'
export TEST_POSTGRES_RESET_CONFIRM='YES_RESET_DISPOSABLE_TEST_DATABASE'

# Temiz test veritabanına migration + PostgreSQL entegrasyon testleri
python -m pytest -q tests/test_postgres_integration.py

# Ardından SQLite regresyon paketi (ayrı DB)
DATABASE_URL='sqlite+pysqlite:///:memory:' python -m pytest -q

# Test hizmetini durdur ve geçici DB'yi kaldır
 docker compose -f docker-compose.test.yml down
```

**Yıkıcı test korumaları:** PostgreSQL fixture herhangi bir bağlantı açmadan önce `TEST_POSTGRES_URL` sürücüsünü `postgresql+psycopg`, host'u loopback, kullanıcı adını `test` içeren bir ad, veritabanı adını `_test`/`_testing` son eki ve `TEST_POSTGRES_RESET_CONFIRM` değerini açık onay olarak doğrular. `ENVIRONMENT=production` iken reddeder; ayrıca `DATABASE_URL` aynı host/port/veritabanını gösteriyorsa reddeder. Ardından bağlandığı sunucunun PostgreSQL 14+ olduğunu, `current_database()` ve `current_user` değerlerinin URL ile eşleştiğini doğrular. Veritabanı boş değilse migration veya temizleme yapmadan testi durdurur. Fixture yalnızca bu doğrulamalardan sonra migration uygular ve test sonunda yalnızca doğrulanmış test veritabanındaki şemayı temizler.

Test URL'si verilmezse entegrasyon testi `SKIPPED` olur; bu PostgreSQL testi başarısı değildir. Test URL'si verilip güvenlik koşullarından biri sağlanmazsa test `FAILED` olur ve bağlantı açılmaz. Gerçek PostgreSQL testi çalıştırılmadan PostgreSQL desteği doğrulanmış sayılmaz.

### Ayrı geliştirme PostgreSQL servisi

Geliştirme veritabanı test veritabanından farklı compose dosyası, port ve kalıcı volume kullanır:

```bash
# Shell'e yalnızca yerel geliştirme için bir parola verin; gerçek üretim sırrı kullanmayın.
export DEV_POSTGRES_PASSWORD='local-development-only-change-this'
docker compose -f docker-compose.dev.yml up -d --wait postgres-dev
# URL örneği: postgresql+psycopg://rea_dev:<parola>@127.0.0.1:55431/real_estate_dev
```

Geliştirme servisi test fixture tarafından hedeflenmez; entegrasyon testi URL'si test veritabanı ismi ve kullanıcı şartlarını sağlamalıdır. Üretim veritabanı URL'sini `TEST_POSTGRES_URL` olarak kullanmayın.


## Yerel demo hesabı ve emsal değerleme

Geliştirme ortamında migration'lar uygulandıktan sonra backend başlangıcında `demo` hesabı otomatik hazırlanır: kullanıcı adı `demo`, parola `demo12345678`. Yerel varsayılan veritabanı `backend/data/real_estate_dev.db` dosyasıdır; PostgreSQL zorunlu değildir.

`GET /api/v1/analytics/valuation` il, ilçe, mahalle, konut türü ve alan bilgilerini alır; önce seçilen mahalledeki aktif benzer ilanları arar, 3'ten az emsal varsa aynı ilçedeki mahalleleri kullanır. Veri yoksa fiyat uydurmaz. Bu bir ilan fiyatı ön tahminidir, ekspertiz değildir.

Yönetici `DELETE /api/v1/users/{id}` ile kullanıcı silebilir. Kullanıcının oluşturduğu ilanlar varsa veri ilişkilerini korumak için silme reddedilir; önce ilan sahipliğinin devredilmesi gerekir. Kendi hesabı veya son aktif yönetici silinemez.
