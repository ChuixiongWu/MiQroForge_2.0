import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { setToken, setStoredUser } from '../lib/auth'
import { postJSON } from '../api/client'

// ─── Chemistry quotes ──────────────────────────────────────────────────────────

const QUOTES = [
  { text: '我来，我见，我计算。', author: '佚名（致敬凯撒）' },
  { text: '一个化学家没有分子轨道理论，就像一个水手没有罗盘。', author: 'Kenichi Fukui' },
  { text: '计算化学的本质是用物理学原理来理解和预测化学现象。', author: 'John Pople' },
  { text: '对于化学家来说，计算机就是他们的显微镜。', author: 'Roald Hoffmann' },
  { text: '一个方程式如果不能预测新的事实，就没有任何价值。', author: 'Paul Dirac' },
  { text: '化学最重要的一条原理：结构决定性质。', author: 'Linus Pauling' },
  { text: '科学计算是人类思维的一种延伸，它使我们看到以前无法看到的事物。', author: '佚名' },
  { text: '计算机之于化学家，正如望远镜之于天文学家。', author: 'Martin Karplus' },
  { text: '在计算中，我们寻求的不是数字，而是理解。', author: 'E. Bright Wilson' },
  { text: '每次计算都是对自然的一次对话。', author: '量子化学格言' },
]

function useRandomQuote() {
  const [quote] = useState(() => QUOTES[Math.floor(Math.random() * QUOTES.length)])
  return quote
}

// ─── LoginPage ────────────────────────────────────────────────────────────────

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const quote = useRandomQuote()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!username.trim() || !password) {
      setError('请输入用户名和密码')
      return
    }

    setLoading(true)
    try {
      const data = await postJSON<{ access_token: string; username: string; role: string }>(
        '/auth/login',
        { username: username.trim(), password },
      )
      setToken(data.access_token)
      setStoredUser({ username: data.username, role: data.role })
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-mf-base">
      <div className="w-full max-w-sm p-8 bg-mf-panel rounded-lg border border-mf-border shadow-lg">
        {/* Header */}
        <h1 className="text-2xl font-bold text-center text-mf-text tracking-tight">
          MiQroForge <span className="text-[11px] text-mf-muted font-normal border border-mf-border rounded px-1 align-super">2.0</span>
        </h1>
        <p className="text-[13px] text-center text-mf-muted mt-1">
          量子与AI赋能化学计算
        </p>

        {/* Quote */}
        <p className="text-[11px] text-center text-mf-muted italic mt-3 mb-6 leading-relaxed">
          &ldquo;{quote.text}&rdquo;
          <br />
          <span className="not-italic text-[10px]">— {quote.author}</span>
        </p>

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-mf-text mb-1">
              用户名
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              className="w-full px-3 py-2 bg-mf-base border border-mf-border rounded text-mf-text
                         placeholder-mf-muted focus:outline-none focus:ring-1 focus:ring-mf-accent"
              placeholder="输入用户名"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-mf-text mb-1">
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full px-3 py-2 bg-mf-base border border-mf-border rounded text-mf-text
                         placeholder-mf-muted focus:outline-none focus:ring-1 focus:ring-mf-accent"
              placeholder="输入密码"
            />
          </div>

          {error && (
            <div className="p-2 text-sm text-red-400 bg-red-900/20 rounded border border-red-800">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-mf-accent text-white rounded font-medium
                       hover:bg-mf-accent-hover disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {loading ? '登录中...' : '登 录'}
          </button>
        </form>
      </div>
    </div>
  )
}
