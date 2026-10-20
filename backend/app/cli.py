"""Operational commands. No default credentials are created automatically."""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def create_admin() -> int:
    email = input("Yönetici e-posta adresi: ").strip().lower()
    username = input("Yönetici kullanıcı adı: ").strip().lower()
    full_name = input("Yönetici adı: ").strip()
    password = getpass.getpass("Yeni yönetici parolası (en az 16 karakter): ")
    confirm = getpass.getpass("Parolayı tekrar girin: ")
    if len(password) < 16 or password != confirm:
        print("Hata: Parolalar eşleşmeli ve en az 16 karakter olmalı.", file=sys.stderr)
        return 2
    if email.count("@") != 1 or "." not in email.rsplit("@", 1)[-1] or not full_name:
        print("Hata: E-posta ve ad geçerli olmalı.", file=sys.stderr)
        return 2
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Hata: Veritabanında kullanıcı var. Bootstrap komutu yalnızca ilk kullanıcı için çalışır.", file=sys.stderr)
            return 3
        user = User(email=email, username=username, full_name=full_name, password_hash=hash_password(password), role="admin", is_active=True)
        db.add(user)
        db.commit()
        print(f"Yönetici oluşturuldu: {email}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Real Estate Analytics operasyon komutları")
    parser.add_argument("command", choices=["create-admin"])
    args = parser.parse_args()
    if args.command == "create-admin":
        return create_admin()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
