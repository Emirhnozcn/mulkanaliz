"""Create or reset a local-only demo account. Run after applying Alembic migrations."""
import os
from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User

EMAIL = os.getenv("TEST_ACCOUNT_EMAIL", "demo@emlak.local")
USERNAME = os.getenv("TEST_ACCOUNT_USERNAME", "demo")
PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD", "demo12345678")
NAME = os.getenv("TEST_ACCOUNT_NAME", "Demo Emlak Danışmanı")

def main():
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise SystemExit("Test hesabı production ortamında oluşturulamaz.")
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where((User.username == USERNAME) | (User.email == EMAIL)))
        if user is None:
            user = User(email=EMAIL, username=USERNAME, full_name=NAME, role="admin", password_hash=hash_password(PASSWORD), is_active=True)
            db.add(user)
        else:
            user.email = EMAIL
            user.username = USERNAME
            user.password_hash = hash_password(PASSWORD)
            user.full_name = NAME
            user.role = "admin"
            user.is_active = True
            user.token_version += 1
        db.commit()
        print(f"Test hesabı hazır: kullanıcı adı={USERNAME}")
        print("Parola TEST_ACCOUNT_PASSWORD ortam değişkeninden alınır; varsayılanı yalnızca yerel test içindir.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
