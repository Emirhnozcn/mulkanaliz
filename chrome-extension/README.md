# Emlak İlan Aktarıcı — Chrome MV3

Manifest V3 + TypeScript eklentisi. Yalnızca danışman eklenti penceresini açıp **Açık sayfadan verileri çıkar** düğmesine bastığında mevcut sekmenin erişilebilir DOM içeriğini ve JSON-LD/meta verilerini okur. Arka planda gezinme/tarama yapmaz, CAPTCHA veya erişim korumalarını aşmaz.

## Geliştirme / kurulum

1. Chrome'da yalnızca kullanımına izin verilen ilan sayfasını açın.
2. `npm install` ve `npm run build` çalıştırın.
3. Chrome `chrome://extensions` → Developer mode → **Load unpacked** → bu `chrome-extension/` klasörünü seçin.
4. Popup'ta API adresini girin (varsayılan `http://localhost:8000`), e-posta/parolanızla **API hesabıyla giriş yapın** ve önceden tanımlanmış konum ID'sini girin.
5. İlan sayfasında eklentiyi açıp **Açık sayfadan verileri çıkar** düğmesine basın.
6. Çıkarılan tüm alanları doğrulayın/düzeltin; eksik fiyatı ve arsa/tarla parsel alanını elle girin; son olarak **Kontrol ettim, sisteme aktar** düğmesine basın.

## API girişi, güvenlik ve CORS

Varsayılan API `http://localhost:8000`'dır. API adresine erişmek için Chrome'un isteğe bağlı host izni ayrıca sorulur. Eklentinin uzantı origin'ini backend `.env` içindeki `CORS_ORIGINS` listesine ekleyin (Chrome uzantı ID'sine bağlı `chrome-extension://<extension-id>`). Yerel denemede backend'i güvenilir makinede çalıştırın.

**Kimlik doğrulama:** Eklenti `/api/v1/auth/login` üzerinden mevcut hesabınızla giriş yapar ve ilan aktarımında `Authorization: Bearer ...` token'ı gönderir. Token Chrome eklentisinin yerel depolamasında tutulur; ortak bilgisayarda kullanıyorsanız eklentinin depolama verisini temizleyin. API'yi internete açmadan önce HTTPS, güçlü sırlar ve uygun yetkilendirme yapılandırması gerekir.

## Çıkarımın sınırları

Genel Schema.org JSON-LD, Open Graph/meta etiketleri ve görünür metindeki yaygın Türkçe alan etiketleri okunur. Kaynağa özel HTML adaptörleri eklenmemiştir; her sitede aynı doğruluk beklenmemelidir. Bilgi tahmin edilmez; eksikler uyarıyla gösterilir ve kullanıcı tarafından doldurulur. Harici ilan kimliği yoksa API kaynak URL'si ile tekrarları eşleştirmeye çalışır. Sayfanın kullanım şartları ve veri kullanım hakları entegrasyondan önce değerlendirilmelidir.

## Test/derleme

```bash
npm run typecheck
npm run build
```

Bu kontroller derlemeyi doğrular; gerçek ilan sitelerinde çıkarım doğruluğu veya canlı API bağlantısı için entegrasyon testi yerine geçmez.
