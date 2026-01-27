# CashUp - Gestão Financeira para Pequenas Empresas

Aplicação web completa para controle financeiro interno com foco em fluxo de caixa, contas a pagar/receber, conciliação manual e relatórios. Implementada com FastAPI + SQLite e frontend React.

## Visão Geral

- **Backend**: FastAPI (REST)
- **Banco**: SQLite (padrão), com script SQL disponível
- **Frontend**: React (Vite)
- **Autenticação**: JWT com níveis de permissão (admin, finance, viewer)
- **Porta padrão**: **9020**

## Modelagem de Dados (ERD)

```
Users (1) ──< ActionLogs

Banks (1) ──< Accounts (1) ──< Transactions

Categories (1) ──< Transactions

Titles ──< Transactions (liquidação)

ReconciliationItems (opcional) ──(match)── Transactions
```

## Estrutura de Diretórios

```
backend/       # API FastAPI
frontend/      # React + Vite
deploy/        # Script de deploy completo
```

## Endpoints Principais

### Autenticação
- `POST /api/auth/login`
- `POST /api/auth/users`
- `GET /api/auth/users`

### Contas/Bancos
- `POST /api/accounts/banks`
- `GET /api/accounts/banks`
- `POST /api/accounts`
- `GET /api/accounts`
- `GET /api/accounts/{id}/balance`

### Categorias e Centros de Custo
- `POST /api/categories`
- `GET /api/categories`
- `POST /api/categories/cost-centers`
- `GET /api/categories/cost-centers`

### Lançamentos
- `POST /api/transactions`
- `GET /api/transactions`

### Contas a Pagar/Receber
- `POST /api/titles`
- `GET /api/titles`
- `POST /api/titles/{id}/settle`

### Fluxo de Caixa
- `GET /api/cashflow/summary`
- `GET /api/cashflow/projection`

### Conciliação
- `POST /api/reconciliation/import`
- `GET /api/reconciliation`

### Relatórios
- `GET /api/reports/cashflow`
- `GET /api/reports/by-category`
- `GET /api/reports/by-account`
- `GET /api/reports/overdue`

## Exemplos de Payloads

### Login
```json
{
  "email": "admin@cashup.local",
  "password": "admin123"
}
```

### Criar Conta
```json
{
  "name": "Nubank PJ",
  "account_type": "corrente",
  "initial_balance": 1200,
  "is_active": true,
  "bank_id": 1
}
```

### Lançamento Financeiro
```json
{
  "transaction_type": "Entrada",
  "date": "2024-08-01",
  "value": 3500,
  "category_id": 1,
  "account_id": 1,
  "payment_method": "PIX",
  "description": "Mensalidade de serviços",
  "client_supplier": "Cliente ABC",
  "document_number": "NF-123",
  "notes": "Pago antecipado",
  "invoice_number": "0001",
  "tax_id": "12.345.678/0001-90"
}
```

### Criar Título a Pagar/Receber
```json
{
  "title_type": "Receber",
  "client_supplier": "Cliente ABC",
  "due_date": "2024-08-15",
  "value": 4500,
  "status": "Pendente",
  "account_id": 1,
  "payment_method": "Boleto",
  "notes": "Serviços de consultoria"
}
```

## Scripts e Banco

- Script SQL: `backend/sql/create_tables.sql`
- Script de inicialização com usuário admin e dados base: `backend/scripts/init_db.py`

Usuário padrão criado:
- Email: `admin@cashup.local`
- Senha: `admin123`

## Rodando Localmente

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 9020
```

### Frontend
```bash
cd frontend
npm install
npm run build
```

Após o build, o backend irá servir o frontend em `http://localhost:9020`.

## Deploy Automatizado (Ubuntu 24.04)

Execute o script (com o repositório em `/opt/cashup`):

```bash
sudo bash deploy/setup.sh
```

O script:
- Cria virtualenv
- Instala dependências
- Inicializa o banco
- Faz build do frontend
- Cria serviço systemd `cashup.service` na porta **9020**

## Exportações (CSV/PDF)

O backend entrega dados estruturados via JSON. Para exportação em CSV/PDF, use o endpoint de relatórios e exporte via frontend.

## Observações

- A conciliação aceita CSV simples com colunas `date,description,value,external_id`.
- A liquidação de títulos gera lançamento automaticamente, vinculando ao título.
