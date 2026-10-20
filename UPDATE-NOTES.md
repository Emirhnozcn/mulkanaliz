# MülkAnaliz update notes

## Included in this package
- Existing username-based login and password hashing.
- Existing admin-only office registration code panel (`/users`) and registration flow without asking for an email in the UI.
- Existing parking field (`has_parking`) on residential quick-create.
- New `/compare` page for selecting up to four active listings and comparing available listing fields.
- New `/tools/investment` calculator for gross/net rental yield, vacancy, recurring expenses, acquisition costs, net cash flow, payback period, and a user-specified five-year appreciation scenario.
- New `/tools/valuation` reference estimator using the existing API's median asking-price-per-square-metre statistic. It explicitly labels the output as a rough asking-price reference, not a formal valuation or confidence interval.
- Existing neighborhood analytics, advanced filters, saved filters, price history, exports, and dashboard price summaries remain available.

## Verification
- Backend tests: `53 passed, 2 skipped` (`python -m pytest -q`).
- The two skipped tests require `TEST_POSTGRES_URL`; no live PostgreSQL integration run was performed in this environment.
- Frontend build/typecheck could not be completed in this environment because `npm ci` did not finish before the environment timeout. Run `npm ci`, `npm run typecheck`, and `npm run build` locally before production use.

## Known scope limits
- A geographic map view with reliable coordinates is not included in this update.
- A persistent customer CRM (customer records, preferences, follow-up tasks) is not included in this update.
- The comparison page compares fields returned by the current listing API; it does not yet join all property/residential detail fields such as net area, building age, elevator, or parking into the comparison table.
- The valuation tool is a transparent baseline calculation from current portfolio asking prices, not a trained ML model or appraisal. For useful results, filter by property type and neighborhood and use verified transaction data when available.


## Satılık / kiralık ayrımı
- İlan kayıtlarına `transaction_type` eklendi (`sale` / `rent`); mevcut kayıtlar migration ile `sale` olarak varsayılanlanır. Mevcut kayıtların gerçekte kiralık olması mümkünse migration sonrasında elle düzeltilmelidir.
- Emsal değerleme artık aynı konum ve özellikler için iki ayrı sonuç döndürür: satılık tahmini ve aylık kiralık tahmini. İki tahmin kendi işlem türündeki aktif ilanlardan hesaplanır; veri yoksa tahmin gösterilmez.
- Chrome aktarım önizlemesine satılık/kiralık seçimi eklendi.
- Migration: `0004_listing_transaction_type`.

## 18.10.2026 — İlan ayırt edilebilirliği ve konum çıkarımı düzeltmeleri
- İlan tablosuna kalıcı `title` alanı eklendi (Alembic `0006_listing_title`); içe aktarılan ilan başlığı API yanıtında saklanır.
- İlan listesi artık başlığı, dahili kayıt/gayrimenkul kimliklerini, harici ilan numarasını, satılık/kiralık türünü ve kaynağı birlikte gösterir. Başlık olmayan eski kayıtlar için güvenli geri dönüş metni kullanılır.
- İlan detay ekranında başlık ve işlem türü gösterilir.
- Chrome eklentisinin konum çıkarımında bir tek CSS sınıfına bağlı kalmak yerine birden fazla breadcrumb DOM seçicisi ayrı ayrı denenir; il adı içermeyen navigasyon kırıntılarının konum sonuçlarını gölgelemesi engellenir.
- Eklenti `npm run typecheck` ve `npm run build` kontrollerinden geçti.
- Backend `python -m compileall -q app tests alembic` ve `python -m pytest -q`: 55 passed, 2 skipped. Atlananlar TEST_POSTGRES_URL gerektiren PostgreSQL entegrasyon testleridir.
- Nuxt frontend için `npm ci` bu çalışma ortamında zaman aşımına uğradı; frontend build/typecheck doğrulanamadı. Canlı Sahibinden sayfasında uçtan uca test yapılamadı.
