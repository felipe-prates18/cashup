from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import ActionLog, PayableReceivable, Transaction
from ..schemas import TitleCreate, TitleOut

router = APIRouter(prefix="/api/titles", tags=["Contas a Pagar/Receber"])


@router.post("", response_model=TitleOut)
def create_title(payload: TitleCreate, db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    title = PayableReceivable(**payload.model_dump())
    db.add(title)
    db.commit()
    db.refresh(title)
    log = ActionLog(user_id=user.id, action="Criou", entity="Title", entity_id=title.id)
    db.add(log)
    db.commit()
    return title


@router.get("", response_model=list[TitleOut])
def list_titles(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(PayableReceivable).all()


@router.post("/{title_id}/settle", response_model=TitleOut)
def settle_title(title_id: int, db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    title = db.query(PayableReceivable).filter(PayableReceivable.id == title_id).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    if title.status in ("Pago", "Recebido"):
        return title
    transaction_type = "Entrada" if title.title_type == "Receber" else "Saída"
    transaction = Transaction(
        transaction_type=transaction_type,
        date=title.due_date,
        value=title.value,
        category_id=1,
        account_id=title.account_id or 1,
        payment_method=title.payment_method or "PIX",
        description=f"Liquidação título {title.id}",
        client_supplier=title.client_supplier,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    title.status = "Recebido" if title.title_type == "Receber" else "Pago"
    title.transaction_id = transaction.id
    db.add(title)
    db.commit()
    log = ActionLog(user_id=user.id, action="Pagou/Recebeu", entity="Title", entity_id=title.id)
    db.add(log)
    db.commit()
    return title
