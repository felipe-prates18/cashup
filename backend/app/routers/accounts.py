from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import Account, Bank, PayableReceivable, Transaction
from ..schemas import AccountCreate, AccountOut, AccountUpdate, BankCreate, BankOut

router = APIRouter(prefix="/api/accounts", tags=["Contas"])


@router.post("/banks", response_model=BankOut)
def create_bank(payload: BankCreate, db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    bank = Bank(**payload.model_dump())
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


@router.get("/banks", response_model=list[BankOut])
def list_banks(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(Bank).all()


@router.post("", response_model=AccountOut)
def create_account(payload: AccountCreate, db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    account = Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(Account).all()


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("finance"))
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    account.is_active = payload.is_active
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("finance"))
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    has_transactions = db.query(Transaction).filter(Transaction.account_id == account_id).first()
    if has_transactions:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir uma conta com lançamentos vinculados."
        )

    has_titles = db.query(PayableReceivable).filter(PayableReceivable.account_id == account_id).first()
    if has_titles:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir uma conta com títulos vinculados."
        )

    db.delete(account)
    db.commit()


@router.get("/{account_id}/balance")
def account_balance(account_id: int, db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    account = db.query(Account).filter(Account.id == account_id).first()
    transactions = db.query(Transaction).filter(Transaction.account_id == account_id).all()
    total = account.initial_balance if account else 0
    for transaction in transactions:
        if transaction.transaction_type == "Entrada":
            total += transaction.value
        else:
            total -= transaction.value
    return {"account_id": account_id, "balance": total}
