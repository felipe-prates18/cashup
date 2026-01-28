import { useEffect, useMemo, useState } from 'react'
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

type User = {
  id: number
  name: string
  email: string
  role: string
  is_active: boolean
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {children}
    </div>
  )
}

const formatCurrency = (value: number) =>
  value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const parseDateValue = (value?: string) => (value ? new Date(`${value}T00:00:00`) : null)

const parseNumberValue = (value: string) => {
  const normalized = value.replace(/\./g, '').replace(',', '.')
  const parsed = Number(normalized)
  return Number.isNaN(parsed) ? 0 : parsed
}

export default function App() {
  const [active, setActive] = useState<Section>('Dashboard')
  const [token, setToken] = useState('')
  const [user, setUser] = useState<User | null>(null)
  const [authError, setAuthError] = useState('')
  const [loginForm, setLoginForm] = useState({ email: '', password: '' })
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [accounts, setAccounts] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [transactions, setTransactions] = useState<any[]>([])
  const [titles, setTitles] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [summary, setSummary] = useState<any | null>(null)
  const [showProfile, setShowProfile] = useState(false)
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })
  const [transactionRange, setTransactionRange] = useState({ start: '', end: '' })
  const [reportRange, setReportRange] = useState({ start: '', end: '' })
  const [accountForm, setAccountForm] = useState({
    name: '',
    account_type: 'Conta Corrente',
    initial_balance: '0',
    is_active: true,
    bank_id: ''
  })
  const [categoryForm, setCategoryForm] = useState({
    name: '',
    category_type: 'Receita',
    parent_id: ''
  })
  const [transactionForm, setTransactionForm] = useState({
    transaction_type: 'Entrada',
    date: '',
    value: '',
    category_id: '',
    account_id: '',
    payment_method: '',
    description: '',
    client_supplier: '',
    document_number: '',
    notes: '',
    invoice_number: '',
    tax_id: ''
  })
  const [titleForm, setTitleForm] = useState({
    title_type: 'Receber',
    client_supplier: '',
    due_date: '',
    value: '',
    status: 'Pendente',
    account_id: '',
    payment_method: '',
    notes: ''
  })
  const [userForm, setUserForm] = useState({
    name: '',
    email: '',
    role: 'viewer',
    password: '',
    is_active: true
  })
  const [formMessage, setFormMessage] = useState('')

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

  useEffect(() => {
    const savedToken = window.localStorage.getItem('cashup-token')
    const savedTheme = window.localStorage.getItem('cashup-theme') as 'light' | 'dark' | null
    if (savedToken) {
      setToken(savedToken)
    }
    if (savedTheme === 'dark' || savedTheme === 'light') {
      setTheme(savedTheme)
    }
  }, [])

  useEffect(() => {
    document.body.dataset.theme = theme
    window.localStorage.setItem('cashup-theme', theme)
  }, [theme])

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }
    window.localStorage.setItem('cashup-token', token)
    apiFetch<User>('/auth/me', { headers: authHeaders })
      .then(setUser)
      .catch(() => setUser(null))
  }, [token])

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

  useEffect(() => {
    if (user?.role === 'admin') {
      apiFetch('/auth/users', { headers: authHeaders }).then(setUsers).catch(() => setUsers([]))
    } else {
      setUsers([])
    }
  }, [user?.role])

  const availableSections = useMemo(() => {
    const adminOnly = new Set<Section>(['Contas', 'Categorias', 'Usuários'])
    if (user?.role === 'admin') {
      return sections
    }
    return sections.filter((section) => !adminOnly.has(section))
  }, [user?.role])

  useEffect(() => {
    if (!availableSections.includes(active)) {
      setActive(availableSections[0])
    }
  }, [availableSections, active])

  const sortedTransactions = useMemo(() => {
    return [...transactions].sort((a, b) => (a.date || '').localeCompare(b.date || ''))
  }, [transactions])

  const filteredTransactions = useMemo(() => {
    const start = parseDateValue(transactionRange.start)
    const end = parseDateValue(transactionRange.end)
    return sortedTransactions.filter((transaction) => {
      const date = parseDateValue(transaction.date)
      if (!date) return false
      if (start && date < start) return false
      if (end && date > end) return false
      return true
    })
  }, [sortedTransactions, transactionRange])

  const filteredReportTransactions = useMemo(() => {
    const start = parseDateValue(reportRange.start)
    const end = parseDateValue(reportRange.end)
    return sortedTransactions.filter((transaction) => {
      const date = parseDateValue(transaction.date)
      if (!date) return false
      if (start && date < start) return false
      if (end && date > end) return false
      return true
    })
  }, [sortedTransactions, reportRange])

  const transactionBalances = useMemo(() => {
    let running = 0
    return filteredTransactions.map((transaction) => {
      const value = Number(transaction.value || 0)
      const signed = transaction.transaction_type === 'Saída' ? -Math.abs(value) : value
      running += signed
      return { transaction, signed, running }
    })
  }, [filteredTransactions])

  const reportBalances = useMemo(() => {
    let running = 0
    return filteredReportTransactions.map((transaction) => {
      const value = Number(transaction.value || 0)
      const signed = transaction.transaction_type === 'Saída' ? -Math.abs(value) : value
      running += signed
      return { transaction, signed, running }
    })
  }, [filteredReportTransactions])

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault()
    setAuthError('')
    setFormMessage('')
    try {
      const response = await apiFetch<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm)
      })
      setToken(response.access_token)
      setLoginForm({ email: '', password: '' })
    } catch (error) {
      setAuthError('Não foi possível autenticar. Verifique email e senha.')
    }
  }

  const handleLogout = () => {
    setToken('')
    setUser(null)
    setSummary(null)
    setAccounts([])
    setCategories([])
    setTransactions([])
    setTitles([])
    setUsers([])
    window.localStorage.removeItem('cashup-token')
  }

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault()
    setFormMessage('')
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setFormMessage('A confirmação da senha não confere.')
      return
    }
    try {
      await apiFetch('/auth/change-password', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      })
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
      setFormMessage('Senha atualizada com sucesso!')
      setShowProfile(false)
    } catch (error) {
      setFormMessage('Não foi possível atualizar a senha.')
    }
  }

  const handleExportCsv = () => {
    const rows = reportBalances.map(({ transaction, signed, running }) => [
      transaction.date,
      transaction.description,
      transaction.payment_method,
      signed.toFixed(2),
      running.toFixed(2)
    ])
    const header = ['Data', 'Descrição', 'Histórico', 'Valor', 'Saldo']
    const csv = [header, ...rows]
      .map((line) => line.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `relatorio-lancamentos-${reportRange.start || 'inicio'}-${
      reportRange.end || 'fim'
    }.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleCreateAccount = async (event: React.FormEvent) => {
    event.preventDefault()
    setFormMessage('')
    try {
          await apiFetch('/accounts', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: accountForm.name,
          account_type: accountForm.account_type,
          initial_balance: parseNumberValue(accountForm.initial_balance || '0'),
          is_active: accountForm.is_active,
          bank_id: accountForm.bank_id ? Number(accountForm.bank_id) : null
        })
      })
      setAccountForm({
        name: '',
        account_type: 'Conta Corrente',
        initial_balance: '0',
        is_active: true,
        bank_id: ''
      })
      apiFetch('/accounts', { headers: authHeaders }).then(setAccounts)
      setFormMessage('Conta criada com sucesso!')
    } catch (error) {
      setFormMessage('Não foi possível salvar a conta.')
    }
  }

  const handleCreateCategory = async (event: React.FormEvent) => {
    event.preventDefault()
    setFormMessage('')
    try {
      await apiFetch('/categories', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: categoryForm.name,
          category_type: categoryForm.category_type,
          parent_id: categoryForm.parent_id ? Number(categoryForm.parent_id) : null
        })
      })
      setCategoryForm({ name: '', category_type: 'Receita', parent_id: '' })
      apiFetch('/categories', { headers: authHeaders }).then(setCategories)
      setFormMessage('Categoria criada com sucesso!')
    } catch (error) {
      setFormMessage('Não foi possível salvar a categoria.')
    }
  }

  const handleCreateTransaction = async (event: React.FormEvent) => {
    event.preventDefault()
    setFormMessage('')
    try {
          await apiFetch('/transactions', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          transaction_type: transactionForm.transaction_type,
          date: transactionForm.date,
          value: parseNumberValue(transactionForm.value || '0'),
          category_id: Number(transactionForm.category_id),
          account_id: Number(transactionForm.account_id),
          payment_method: transactionForm.payment_method,
          description: transactionForm.description,
          client_supplier: transactionForm.client_supplier || null,
          document_number: transactionForm.document_number || null,
          notes: transactionForm.notes || null,
          invoice_number: transactionForm.invoice_number || null,
          tax_id: transactionForm.tax_id || null,
          document_path: null
        })
      })
      setTransactionForm({
        transaction_type: 'Entrada',
        date: '',
        value: '',
        category_id: '',
        account_id: '',
        payment_method: '',
        description: '',
        client_supplier: '',
        document_number: '',
        notes: '',
        invoice_number: '',
        tax_id: ''
      })
      apiFetch('/transactions', { headers: authHeaders }).then(setTransactions)
      apiFetch('/cashflow/summary', { headers: authHeaders }).then(setSummary)
      setFormMessage('Lançamento criado com sucesso!')
    } catch (error) {
      setFormMessage('Não foi possível salvar o lançamento.')
    }
  }

  const handleCreateTitle = async (event: React.FormEvent) => {
    event.preventDefault()
    setFormMessage('')
    try {
          await apiFetch('/titles', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          title_type: titleForm.title_type,
          client_supplier: titleForm.client_supplier,
          due_date: titleForm.due_date,
          value: parseNumberValue(titleForm.value || '0'),
          status: titleForm.status,
          account_id: titleForm.account_id ? Number(titleForm.account_id) : null,
          payment_method: titleForm.payment_method || null,
          notes: titleForm.notes || null
        })
      })
      setTitleForm({
        title_type: 'Receber',
        client_supplier: '',
        due_date: '',
        value: '',
        status: 'Pendente',
        account_id: '',
        payment_method: '',
        notes: ''
      })
      apiFetch('/titles', { headers: authHeaders }).then(setTitles)
      setFormMessage('Título cadastrado com sucesso!')
    } catch (error) {
      setFormMessage('Não foi possível salvar o título.')
    }
  }

  const handleCreateUser = async (event: React.FormEvent) => {
    event.preventDefault()
    setFormMessage('')
    try {
      await apiFetch('/auth/users', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify(userForm)
      })
      setUserForm({ name: '', email: '', role: 'viewer', password: '', is_active: true })
      apiFetch('/auth/users', { headers: authHeaders }).then(setUsers)
      setFormMessage('Usuário criado com sucesso!')
    } catch (error) {
      setFormMessage('Não foi possível salvar o usuário.')
    }
  }

  if (!token) {
    return (
      <div className="auth-shell">
        <div className="login-card">
          <div>
            <h1>CashUp</h1>
            <p>Entre com suas credenciais para acessar o painel.</p>
          </div>
          <form onSubmit={handleLogin} className="form-grid">
            <label className="field">
              Email
              <input
                type="email"
                value={loginForm.email}
                onChange={(event) => setLoginForm({ ...loginForm, email: event.target.value })}
                required
              />
            </label>
            <label className="field">
              Senha
              <input
                type="password"
                value={loginForm.password}
                onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })}
                required
              />
            </label>
            {authError && <p className="form-message error">{authError}</p>}
            <button type="submit" className="primary">
              Entrar
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <header>
        <div>
          <h1>CashUp</h1>
          <p>Gestão financeira para pequenas empresas</p>
          {user && <span className="badge">{user.name} · {user.role}</span>}
        </div>
        <div className="header-actions">
          <button className="ghost profile-button" onClick={() => setShowProfile(true)}>
            <span aria-hidden="true">👤</span>
            Perfil
          </button>
          <button className="ghost" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
            {theme === 'light' ? 'Modo escuro' : 'Modo claro'}
          </button>
          <button className="ghost" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>
      <nav>
        {availableSections.map((section) => (
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
        {formMessage && <p className="form-message">{formMessage}</p>}
        {showProfile && (
          <div className="modal-backdrop" role="dialog" aria-modal="true">
            <div className="modal-card">
              <div className="modal-header">
                <h2>Alterar senha</h2>
                <button className="ghost" onClick={() => setShowProfile(false)}>
                  Fechar
                </button>
              </div>
              <form onSubmit={handleChangePassword} className="form-grid">
                <label className="field">
                  Senha atual
                  <input
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(event) =>
                      setPasswordForm({ ...passwordForm, current_password: event.target.value })
                    }
                    required
                  />
                </label>
                <label className="field">
                  Nova senha
                  <input
                    type="password"
                    value={passwordForm.new_password}
                    onChange={(event) =>
                      setPasswordForm({ ...passwordForm, new_password: event.target.value })
                    }
                    required
                  />
                </label>
                <label className="field">
                  Confirmar nova senha
                  <input
                    type="password"
                    value={passwordForm.confirm_password}
                    onChange={(event) =>
                      setPasswordForm({ ...passwordForm, confirm_password: event.target.value })
                    }
                    required
                  />
                </label>
                <button type="submit" className="primary">
                  Atualizar senha
                </button>
              </form>
            </div>
          </div>
        )}
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
                <p>Carregue os dados para acompanhar o caixa.</p>
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
            <form onSubmit={handleCreateAccount} className="form-grid">
              <label className="field">
                Nome
                <input
                  value={accountForm.name}
                  onChange={(event) => setAccountForm({ ...accountForm, name: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Tipo
                <select
                  value={accountForm.account_type}
                  onChange={(event) =>
                    setAccountForm({ ...accountForm, account_type: event.target.value })
                  }
                >
                  <option value="Conta Corrente">Conta Corrente</option>
                  <option value="Conta Digital">Conta Digital</option>
                  <option value="Caixa">Caixa</option>
                  <option value="Poupança">Poupança</option>
                </select>
              </label>
              <label className="field">
                Saldo inicial
                <input
                  type="number"
                  value={accountForm.initial_balance}
                  onChange={(event) =>
                    setAccountForm({ ...accountForm, initial_balance: event.target.value })
                  }
                />
              </label>
              <label className="field">
                Banco (ID opcional)
                <input
                  type="number"
                  value={accountForm.bank_id}
                  onChange={(event) => setAccountForm({ ...accountForm, bank_id: event.target.value })}
                />
              </label>
              <label className="field checkbox">
                <input
                  type="checkbox"
                  checked={accountForm.is_active}
                  onChange={(event) =>
                    setAccountForm({ ...accountForm, is_active: event.target.checked })
                  }
                />
                Conta ativa
              </label>
              <button type="submit" className="primary">
                Criar conta
              </button>
            </form>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Tipo</th>
                    <th>Saldo inicial</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((account) => (
                    <tr key={account.id}>
                      <td>{account.name}</td>
                      <td>{account.account_type}</td>
                      <td>{formatCurrency(Number(account.initial_balance || 0))}</td>
                      <td>{account.is_active ? 'Ativa' : 'Inativa'}</td>
                    </tr>
                  ))}
                  {!accounts.length && (
                    <tr>
                      <td colSpan={4}>Nenhuma conta cadastrada.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>
        )}
        {active === 'Categorias' && (
          <SectionCard title="Categorias e centros de custo">
            <form onSubmit={handleCreateCategory} className="form-grid">
              <label className="field">
                Nome
                <input
                  value={categoryForm.name}
                  onChange={(event) => setCategoryForm({ ...categoryForm, name: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Tipo
                <select
                  value={categoryForm.category_type}
                  onChange={(event) =>
                    setCategoryForm({ ...categoryForm, category_type: event.target.value })
                  }
                >
                  <option value="Receita">Receita</option>
                  <option value="Despesa">Despesa</option>
                </select>
              </label>
              <label className="field">
                Categoria mãe (ID opcional)
                <input
                  type="number"
                  value={categoryForm.parent_id}
                  onChange={(event) =>
                    setCategoryForm({ ...categoryForm, parent_id: event.target.value })
                  }
                />
              </label>
              <button type="submit" className="primary">
                Criar categoria
              </button>
            </form>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Tipo</th>
                    <th>Categoria mãe</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((category) => (
                    <tr key={category.id}>
                      <td>{category.name}</td>
                      <td>{category.category_type}</td>
                      <td>
                        {categories.find((item) => item.id === category.parent_id)?.name || '—'}
                      </td>
                    </tr>
                  ))}
                  {!categories.length && (
                    <tr>
                      <td colSpan={3}>Nenhuma categoria cadastrada.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>
        )}
        {active === 'Lançamentos' && (
          <SectionCard title="Lançamentos financeiros">
            <form onSubmit={handleCreateTransaction} className="form-grid">
              <label className="field">
                Tipo
                <select
                  value={transactionForm.transaction_type}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, transaction_type: event.target.value })
                  }
                >
                  <option value="Entrada">Entrada</option>
                  <option value="Saída">Saída</option>
                </select>
              </label>
              <label className="field">
                Data
                <input
                  type="date"
                  value={transactionForm.date}
                  onChange={(event) => setTransactionForm({ ...transactionForm, date: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Valor
                <input
                  type="number"
                  value={transactionForm.value}
                  onChange={(event) => setTransactionForm({ ...transactionForm, value: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Categoria
                <select
                  value={transactionForm.category_id}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, category_id: event.target.value })
                  }
                  required
                >
                  <option value="">Selecione</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Conta
                <select
                  value={transactionForm.account_id}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, account_id: event.target.value })
                  }
                  required
                >
                  <option value="">Selecione</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Forma de pagamento
                <input
                  value={transactionForm.payment_method}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, payment_method: event.target.value })
                  }
                  required
                />
              </label>
              <label className="field">
                Descrição
                <input
                  value={transactionForm.description}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, description: event.target.value })
                  }
                  required
                />
              </label>
              <label className="field">
                Cliente/Fornecedor
                <input
                  value={transactionForm.client_supplier}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, client_supplier: event.target.value })
                  }
                />
              </label>
              <label className="field">
                Documento
                <input
                  value={transactionForm.document_number}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, document_number: event.target.value })
                  }
                />
              </label>
              <label className="field">
                Nota fiscal
                <input
                  value={transactionForm.invoice_number}
                  onChange={(event) =>
                    setTransactionForm({ ...transactionForm, invoice_number: event.target.value })
                  }
                />
              </label>
              <label className="field">
                CNPJ/CPF
                <input
                  value={transactionForm.tax_id}
                  onChange={(event) => setTransactionForm({ ...transactionForm, tax_id: event.target.value })}
                />
              </label>
              <label className="field full">
                Observações
                <textarea
                  value={transactionForm.notes}
                  onChange={(event) => setTransactionForm({ ...transactionForm, notes: event.target.value })}
                />
              </label>
              <button type="submit" className="primary">
                Criar lançamento
              </button>
            </form>
            <div className="filters">
              <label className="field">
                Data inicial
                <input
                  type="date"
                  value={transactionRange.start}
                  onChange={(event) =>
                    setTransactionRange({ ...transactionRange, start: event.target.value })
                  }
                />
              </label>
              <label className="field">
                Data final
                <input
                  type="date"
                  value={transactionRange.end}
                  onChange={(event) =>
                    setTransactionRange({ ...transactionRange, end: event.target.value })
                  }
                />
              </label>
            </div>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Descrição</th>
                    <th>Histórico</th>
                    <th>Valor (R$)</th>
                    <th>Saldo (R$)</th>
                  </tr>
                </thead>
                <tbody>
                  {transactionBalances.map(({ transaction, signed, running }) => (
                    <tr key={transaction.id}>
                      <td>{transaction.date}</td>
                      <td>{transaction.description}</td>
                      <td>{transaction.payment_method}</td>
                      <td className={signed < 0 ? 'value-negative' : ''}>
                        {formatCurrency(signed)}
                      </td>
                      <td>{formatCurrency(running)}</td>
                    </tr>
                  ))}
                  {!transactionBalances.length && (
                    <tr>
                      <td colSpan={5}>Nenhum lançamento encontrado para o período.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>
        )}
        {active === 'Pagar/Receber' && (
          <SectionCard title="Títulos futuros">
            <form onSubmit={handleCreateTitle} className="form-grid">
              <label className="field">
                Tipo
                <select
                  value={titleForm.title_type}
                  onChange={(event) =>
                    setTitleForm({ ...titleForm, title_type: event.target.value })
                  }
                >
                  <option value="Receber">Receber</option>
                  <option value="Pagar">Pagar</option>
                </select>
              </label>
              <label className="field">
                Cliente/Fornecedor
                <input
                  value={titleForm.client_supplier}
                  onChange={(event) =>
                    setTitleForm({ ...titleForm, client_supplier: event.target.value })
                  }
                  required
                />
              </label>
              <label className="field">
                Vencimento
                <input
                  type="date"
                  value={titleForm.due_date}
                  onChange={(event) => setTitleForm({ ...titleForm, due_date: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Valor
                <input
                  type="number"
                  value={titleForm.value}
                  onChange={(event) => setTitleForm({ ...titleForm, value: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Status
                <select
                  value={titleForm.status}
                  onChange={(event) => setTitleForm({ ...titleForm, status: event.target.value })}
                >
                  <option value="Pendente">Pendente</option>
                  <option value="Pago">Pago</option>
                </select>
              </label>
              <label className="field">
                Conta (opcional)
                <select
                  value={titleForm.account_id}
                  onChange={(event) => setTitleForm({ ...titleForm, account_id: event.target.value })}
                >
                  <option value="">Selecione</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Forma de pagamento
                <input
                  value={titleForm.payment_method}
                  onChange={(event) =>
                    setTitleForm({ ...titleForm, payment_method: event.target.value })
                  }
                />
              </label>
              <label className="field full">
                Observações
                <textarea
                  value={titleForm.notes}
                  onChange={(event) => setTitleForm({ ...titleForm, notes: event.target.value })}
                />
              </label>
              <button type="submit" className="primary">
                Cadastrar título
              </button>
            </form>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Cliente/Fornecedor</th>
                    <th>Vencimento</th>
                    <th>Status</th>
                    <th>Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {titles.map((title) => (
                    <tr key={title.id}>
                      <td>{title.title_type}</td>
                      <td>{title.client_supplier}</td>
                      <td>{title.due_date}</td>
                      <td>{title.status}</td>
                      <td>{formatCurrency(Number(title.value || 0))}</td>
                    </tr>
                  ))}
                  {!titles.length && (
                    <tr>
                      <td colSpan={5}>Nenhum título cadastrado.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
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
            <div className="filters">
              <label className="field">
                Data inicial
                <input
                  type="date"
                  value={reportRange.start}
                  onChange={(event) =>
                    setReportRange({ ...reportRange, start: event.target.value })
                  }
                />
              </label>
              <label className="field">
                Data final
                <input
                  type="date"
                  value={reportRange.end}
                  onChange={(event) => setReportRange({ ...reportRange, end: event.target.value })}
                />
              </label>
              <button type="button" className="secondary" onClick={handleExportCsv}>
                Exportar CSV
              </button>
            </div>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Descrição</th>
                    <th>Histórico</th>
                    <th>Valor (R$)</th>
                    <th>Saldo (R$)</th>
                  </tr>
                </thead>
                <tbody>
                  {reportBalances.map(({ transaction, signed, running }) => (
                    <tr key={transaction.id}>
                      <td>{transaction.date}</td>
                      <td>{transaction.description}</td>
                      <td>{transaction.payment_method}</td>
                      <td className={signed < 0 ? 'value-negative' : ''}>
                        {formatCurrency(signed)}
                      </td>
                      <td>{formatCurrency(running)}</td>
                    </tr>
                  ))}
                  {!reportBalances.length && (
                    <tr>
                      <td colSpan={5}>Selecione um período para visualizar os lançamentos.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>
        )}
        {active === 'Usuários' && (
          <SectionCard title="Usuários e permissões">
            <form onSubmit={handleCreateUser} className="form-grid">
              <label className="field">
                Nome
                <input
                  value={userForm.name}
                  onChange={(event) => setUserForm({ ...userForm, name: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Email
                <input
                  type="email"
                  value={userForm.email}
                  onChange={(event) => setUserForm({ ...userForm, email: event.target.value })}
                  required
                />
              </label>
              <label className="field">
                Role
                <select
                  value={userForm.role}
                  onChange={(event) => setUserForm({ ...userForm, role: event.target.value })}
                >
                  <option value="admin">Admin</option>
                  <option value="finance">Finance</option>
                  <option value="viewer">Viewer</option>
                </select>
              </label>
              <label className="field">
                Senha
                <input
                  type="password"
                  value={userForm.password}
                  onChange={(event) => setUserForm({ ...userForm, password: event.target.value })}
                  required
                />
              </label>
              <label className="field checkbox">
                <input
                  type="checkbox"
                  checked={userForm.is_active}
                  onChange={(event) => setUserForm({ ...userForm, is_active: event.target.checked })}
                />
                Usuário ativo
              </label>
              <button type="submit" className="primary">
                Criar usuário
              </button>
            </form>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Email</th>
                    <th>Perfil</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((item) => (
                    <tr key={item.id}>
                      <td>{item.name}</td>
                      <td>{item.email}</td>
                      <td>{item.role}</td>
                      <td>{item.is_active ? 'Ativo' : 'Inativo'}</td>
                    </tr>
                  ))}
                  {!users.length && (
                    <tr>
                      <td colSpan={4}>Nenhum usuário cadastrado.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </SectionCard>
        )}
      </main>
    </div>
  )
}
