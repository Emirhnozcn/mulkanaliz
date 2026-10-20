# Son düzeltmeler

## 1) Chrome eklentisi: il / ilçe / mahalle otomatik okuma
- Konum artık 5 stratejiyle okunur: Sahibinden konum bağlantıları (address_city/town/quarter), aynı satırdaki bağlantı grupları (İl · İlçe · Mah.), breadcrumb, görünen kısa metin blokları ve meta/başlık yedeği. Eksiksiz sonuç varsa o kullanılır, yoksa kısmi sonuçlar birleştirilir.
- "İhsaniye/Gölyüzü Mah." gibi semt/mahalle biçimleri ve "Mah./Mh./Mahallesi" ekleri temizlenir.
- İl listesindeki `adiyaman` hatası düzeltildi (Adıyaman bulunamıyordu); Türkçe karakter duyarsız eşleştirme eklendi.
- Konum okununca (giriş yapılmışsa) il/ilçe/mahalle API'de aranır, yoksa otomatik oluşturulur ve ilan buna bağlanır.
- `2+1` artık `room_count=3` + `living_room_count=1` olarak kaydedilir (analizler değişmez; ekranda "2+1" görünür). "Stüdyo" → 1+0.
- Eklentiyi yeniden yüklemek için: chrome://extensions → Yenile (dist/popup.js derlenmiş halde pakette).

## 2) Web: ilanların ayırt edilebilmesi
- API (`GET /listings`, `GET /listings/{id}`) artık il/ilçe/mahalle, tür, oda düzeni, m², bina yaşı, kat bilgilerini de döner (veritabanı şeması / migration değişmedi).
- İlan listesi, ilan detayı, panel ve fiyat geçmişi sayfalarında: "📍 Gölyüzü / Merkez / Bolu" + etiketler (Daire · 2+1 · 95 m² net · 5 yaşında · 2. kat / 6). Başlık yoksa "Gölyüzü Mah. · 2+1 · 95 m² · İlan #12" üretilir.

## 3) Aynı ilanın yeniden aktarımı
- Daha önce yanlış/eksik konumla kaydedilmiş ilan tekrar aktarılınca artık 409 hatası vermez; konum düzeltilir.

## Test
- Backend: 51 test geçti (2 yeni). Frontend `nuxt build` başarılı. Eklenti typecheck + build başarılı; konum okuma 7 farklı sahte sayfa yapısıyla test edildi.
- Gerçek Sahibinden sayfası bu ortamdan açılamadığı için canlı doğrulama yapılamadı; önizlemede konumu yine kontrol edin.

---
# 3. tur düzeltmeler

## Yüksek fiyatlar (6.900.000 TL → "7 TL" hatası)
- Eklentideki sayı ayrıştırıcı yalnızca son binlik noktasını siliyordu (6.900.000 → 6,9). Artık "6.900.000 TL", "12.500.000,50", "6900000.00", "6 900 000" doğru okunuyor. Önizleme alanındaki fiyat da aynı mantıkla okunuyor.
- Daha önce yanlış kaydedilmiş ilanlar için: ilanı eklentiyle tekrar aktarın; fiyat güncellenir (fiyat geçmişine de işlenir). İsterseniz ilan düzenleme ekranından da düzeltebilirsiniz.

## Emsale göre fiyat önerisi (Araçlar → Değerleme)
- Konut yanında artık konut imarlı arsa, ticari imarlı arsa ve tarla da değerlenebiliyor (parsel m² üzerinden).
- Oda eşleştirmesi düzeltildi: sistemde oda sayısı toplam olarak tutulur (2+1 = 3); arayüz seçenekleri buna göre yeniden etiketlendi.
- Emsal bulma kademeli: mahalle (alan + oda) → mahalle (alan) → ilçe → alan kısıtı gevşetilmiş ilçe. 1-2 emsal varsa "sınırlı güvenilirlik" notuyla yine tahmin verilir.
- Hatalı girilmiş uç fiyatlar (medyan m² fiyatının 4 katından fazla sapanlar) hesaptan ayıklanır.
- Veritabanındaki arsa kodları (`residential_zoned_land`) ile arayüz/analiz kodları (`residential_land`) uyuşmuyordu; arsa filtreleri ve analizler boş dönüyordu. İki yazım da artık kabul ediliyor.

## Test
- Backend: 58 test geçti (7 yeni değerleme/arsa testi). Frontend `nuxt build` başarılı. Eklenti typecheck/build başarılı; fiyat ayrıştırma 8 farklı biçimle test edildi.
- Not: `nuxt typecheck` komutu vue-tsc/volar sürüm uyumsuzluğundan (proje bağımlılıkları) çöküyor; kodla ilgisi yok, `npm run build` sorunsuz.

---
# 4. tur: gayrimenkul türünün otomatik algılanması
- Eklenti artık Daire / Müstakil ev / Villa / Konut imarlı arsa / Ticari imarlı arsa / Tarla türünü sayfadan kendisi seçiyor ("Emlak Tipi" alanı → kategori kırıntısı → ilan başlığı → ilan adresindeki ad sırasıyla; arsada "İmar Durumu" ince ayar yapar). Algılanamazsa mevcut seçim kalır ve uyarı gösterilir; yine elle değiştirilebilir.
- Arsa/tarla ilanlarında parsel alanı ("m²") otomatik okunur; konuta özgü uyarılar (net/brüt m², oda, kat) gösterilmez.
- 11 farklı sahte sayfa yapısıyla test edildi. Eklentiyi chrome://extensions sayfasından "Yenile"yin.
