from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("ActionLog", back_populates="user")


class Bank(Base):
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    code = Column(String(20), nullable=False)

    accounts = relationship("Account", back_populates="bank")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    account_type = Column(String(50), nullable=False)
    initial_balance = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    bank_id = Column(Integer, ForeignKey("banks.id"))

    bank = relationship("Bank", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    category_type = Column(String(20), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)


class CostCenter(Base):
    __tablename__ = "cost_centers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    payment_method = Column(String(30), nullable=False)
    description = Column(String(255), nullable=False)
    client_supplier = Column(String(120))
    document_number = Column(String(60))
    notes = Column(Text)
    invoice_number = Column(String(60))
    document_path = Column(String(255))
    tax_id = Column(String(30))
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="transactions")


class PayableReceivable(Base):
    __tablename__ = "titles"

    id = Column(Integer, primary_key=True, index=True)
    title_type = Column(String(20), nullable=False)
    client_supplier = Column(String(120), nullable=False)
    due_date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    status = Column(String(20), default="Pendente")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    payment_method = Column(String(30))
    notes = Column(Text)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)


class ReconciliationItem(Base):
    __tablename__ = "reconciliation_items"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(80))
    date = Column(Date, nullable=False)
    description = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    status = Column(String(20), default="Pendente")
    matched_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(40), nullable=False)
    entity = Column(String(60), nullable=False)
    entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")
