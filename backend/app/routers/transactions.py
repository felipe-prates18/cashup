from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import ActionLog, Transaction
from ..schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["Lançamentos"])


@router.post("", response_model=TransactionOut)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    transaction = Transaction(**payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    log = ActionLog(user_id=user.id, action="Criou", entity="Transaction", entity_id=transaction.id)
    db.add(log)
    db.commit()
    return transaction


@router.get("", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(Transaction).order_by(Transaction.date.desc()).all()
