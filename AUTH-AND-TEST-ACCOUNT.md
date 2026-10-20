# Authentication and local demo account

Authentication uses a unique username and a password hash stored in PostgreSQL. Passwords are never stored in plaintext; the backend uses salted scrypt hashes.

After upgrading the database, create/reset the local demo account from `backend`:

```powershell
python scripts/create_test_account.py
```

Local demo credentials:
- Username: `demo`
- Password: `Demo1234!Demo`

The account script refuses to run when `ENVIRONMENT=production`. Do not use these credentials in a deployed environment. The login screen intentionally does not display demo credentials or prefill the form.

Existing users receive temporary usernames such as `user_1` during migration `0003_usernames`; they can sign in with that username until the application provides an account profile flow. New registrations choose a username.


## Ofis davet kodu ve kayıt
- Çalışan kaydında e-posta istenmez; kullanıcı adı benzersizdir. Mevcut veritabanı uyumluluğu için e-posta alanında teslim edilemeyen `@users.invalid` adresi tutulur; bu adres e-posta gönderimi için kullanılmaz.
- Ofis kayıt kodu backend `.env` dosyasındaki `OFFICE_REGISTRATION_CODE` ayarından gelir.
- Yönetici, oturum açtıktan sonra Kullanıcı yönetimi ekranında **Kodu göster** düğmesiyle kodu görebilir ve kopyalayabilir. Bu işlem backend'de yönetici rolüyle korunur.
