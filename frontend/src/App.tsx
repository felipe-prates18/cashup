import { useEffect, useState } from 'react'
import { apiFetch } from './api'

const sections = [
  'Dashboard',
  'Contas',
  'Categorias',
  'Lançamentos',
  'Pagar/Receber',
  'Conciliação',
  'Relatórios',
  'Usuários'
] as const

type Section = (typeof sections)[number]

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {children}
    </div>
  )
}

export default function App() {
  const [active, setActive] = useState<Section>('Dashboard')
  const [token, setToken] = useState('')
  const [accounts, setAccounts] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [transactions, setTransactions] = useState<any[]>([])
  const [titles, setTitles] = useState<any[]>([])
  const [summary, setSummary] = useState<any | null>(null)

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

  useEffect(() => {
    if (!token) {
      return
    }
    apiFetch('/accounts', { headers: authHeaders }).then(setAccounts).catch(() => setAccounts([]))
    apiFetch('/categories', { headers: authHeaders }).then(setCategories).catch(() => setCategories([]))
    apiFetch('/transactions', { headers: authHeaders }).then(setTransactions).catch(() => setTransactions([]))
    apiFetch('/titles', { headers: authHeaders }).then(setTitles).catch(() => setTitles([]))
    apiFetch('/cashflow/summary', { headers: authHeaders }).then(setSummary).catch(() => setSummary(null))
  }, [token])

  return (
    <div className="app">
      <header>
        <div>
          <h1>CashUp</h1>
          <p>Gestão financeira para pequenas empresas</p>
        </div>
        <div className="token">
          <label>Token de acesso</label>
          <input
            type="password"
            placeholder="Cole o token JWT"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
        </div>
      </header>
      <nav>
        {sections.map((section) => (
          <button
            key={section}
            className={section === active ? 'active' : ''}
            onClick={() => setActive(section)}
          >
            {section}
          </button>
        ))}
      </nav>
      <main>
        {active === 'Dashboard' && (
          <div className="grid">
            <SectionCard title="Resumo do Caixa">
              {summary ? (
                <ul>
                  <li>Saldo consolidado: R$ {summary.total_balance?.toFixed(2)}</li>
                  <li>Entradas: R$ {summary.total_in?.toFixed(2)}</li>
                  <li>Saídas: R$ {summary.total_out?.toFixed(2)}</li>
                </ul>
              ) : (
                <p>Informe o token para carregar os dados.</p>
              )}
            </SectionCard>
            <SectionCard title="Contas financeiras">
              <ul>
                {accounts.map((account) => (
                  <li key={account.id}>
                    {account.name} ({account.account_type})
                  </li>
                ))}
              </ul>
            </SectionCard>
            <SectionCard title="Últimos lançamentos">
              <ul>
                {transactions.slice(0, 5).map((transaction) => (
                  <li key={transaction.id}>
                    {transaction.date} - {transaction.description} - R$ {transaction.value}
                  </li>
                ))}
              </ul>
            </SectionCard>
          </div>
        )}
        {active === 'Contas' && (
          <SectionCard title="Cadastro de Contas">
            <p>Use o endpoint /api/accounts para criar ou editar contas financeiras.</p>
            <pre>{JSON.stringify(accounts, null, 2)}</pre>
          </SectionCard>
        )}
        {active === 'Categorias' && (
          <SectionCard title="Categorias e centros de custo">
            <p>Use /api/categories e /api/categories/cost-centers.</p>
            <pre>{JSON.stringify(categories, null, 2)}</pre>
          </SectionCard>
        )}
        {active === 'Lançamentos' && (
          <SectionCard title="Lançamentos financeiros">
            <p>Use /api/transactions para criar entradas e saídas.</p>
            <pre>{JSON.stringify(transactions, null, 2)}</pre>
          </SectionCard>
        )}
        {active === 'Pagar/Receber' && (
          <SectionCard title="Títulos futuros">
            <p>Use /api/titles e /api/titles/{{id}}/settle.</p>
            <pre>{JSON.stringify(titles, null, 2)}</pre>
          </SectionCard>
        )}
        {active === 'Conciliação' && (
          <SectionCard title="Conciliação Bancária">
            <p>Importe OFX ou CSV simples em /api/reconciliation/import.</p>
            <p>O CSV deve ter: date, description, value, external_id.</p>
          </SectionCard>
        )}
        {active === 'Relatórios' && (
          <SectionCard title="Relatórios">
            <p>Endpoints disponíveis:</p>
            <ul>
              <li>/api/reports/cashflow</li>
              <li>/api/reports/by-category</li>
              <li>/api/reports/by-account</li>
              <li>/api/reports/overdue</li>
            </ul>
          </SectionCard>
        )}
        {active === 'Usuários' && (
          <SectionCard title="Usuários e permissões">
            <p>Use /api/auth/users para CRUD (admin).</p>
            <p>Roles disponíveis: admin, finance, viewer.</p>
          </SectionCard>
        )}
      </main>
    </div>
  )
}
