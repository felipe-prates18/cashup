from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class BankBase(BaseModel):
    name: str
    code: str


class BankCreate(BankBase):
    pass


class BankOut(BankBase):
    id: int

    class Config:
        from_attributes = True


class AccountBase(BaseModel):
    name: str
    account_type: str
    initial_balance: float = 0
    is_active: bool = True
    bank_id: Optional[int] = None


class AccountCreate(AccountBase):
    pass


class AccountOut(AccountBase):
    id: int

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str
    category_type: str
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True


class CostCenterBase(BaseModel):
    name: str


class CostCenterCreate(CostCenterBase):
    pass


class CostCenterOut(CostCenterBase):
    id: int

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    transaction_type: str
    date: date
    value: float
    category_id: int
    account_id: int
    payment_method: str
    description: str
    client_supplier: Optional[str] = None
    document_number: Optional[str] = None
    notes: Optional[str] = None
    invoice_number: Optional[str] = None
    document_path: Optional[str] = None
    tax_id: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionOut(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TitleBase(BaseModel):
    title_type: str
    client_supplier: str
    due_date: date
    value: float
    status: str = "Pendente"
    account_id: Optional[int] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class TitleCreate(TitleBase):
    pass


class TitleOut(TitleBase):
    id: int
    transaction_id: Optional[int] = None

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    name: str
    email: str
    role: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ActionLogOut(BaseModel):
    id: int
    action: str
    entity: str
    entity_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class CashflowSummary(BaseModel):
    total_balance: float
    total_in: float
    total_out: float


class ReportItem(BaseModel):
    label: str
    value: float


class ReconciliationItemBase(BaseModel):
    external_id: Optional[str] = None
    date: date
    description: str
    value: float
    status: str = "Pendente"
    matched_transaction_id: Optional[int] = None


class ReconciliationItemOut(ReconciliationItemBase):
    id: int

    class Config:
        from_attributes = True
