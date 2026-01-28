from pathlib import Path
import sys

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.models import Account, Bank, Category, User


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@cashup.local").first()
    if not admin:
        admin = User(
            name="Admin",
            email="admin@cashup.local",
            role="admin",
            password_hash=get_password_hash("admin"),
        )
        db.add(admin)
    else:
        admin.name = "Admin"
        admin.role = "admin"
        admin.is_active = True
        admin.password_hash = get_password_hash("admin")
    if not db.query(Category).first():
        db.add(Category(name="Receitas Gerais", category_type="Receita"))
        db.add(Category(name="Despesas Gerais", category_type="Despesa"))
    if not db.query(Bank).first():
        bank = Bank(name="Banco Interno", code="000")
        db.add(bank)
        db.flush()
        db.add(Account(name="Caixa", account_type="caixa", initial_balance=0, bank_id=bank.id))
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
