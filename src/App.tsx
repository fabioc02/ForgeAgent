import React, { useState, useEffect, useRef } from 'react'
import {
  Terminal, Cpu, Folder, Brain, Settings, MessageSquare,
  Square, Send
} from 'lucide-react'

type Tab = 'chat' | 'projects' | 'terminal' | 'memory' | 'runtime' | 'settings'

interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: string
  toolName?: string
}

interface RuntimeStatus {
  mode: 'gpu' | 'cpu' | 'error'
  model: string
  backend: string
  gpu_name?: string
  status: string
}

interface Project {
  id: string
  name: string
  language: string
  created_at: string
  tasks_count: number
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [runtime, setRuntime] = useState<RuntimeStatus>({
    mode: 'cpu', model: 'loading...', backend: 'transformers', status: 'idle'
  })
  const [projects, setProjects] = useState<Project[]>([])
  const [terminalOutput, setTerminalOutput] = useState<string[]>([])
  const [terminalCmd, setTerminalCmd] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [status, setStatus] = useState<{ api: boolean; bridge: boolean }>({
    api: false, bridge: false
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [temperature, setTemperature] = useState(0.1)
  const [maxTokens, setMaxTokens] = useState(2048)

  // Carregar config do localStorage
  React.useEffect(() => {
    const saved = localStorage.getItem('forge_config')
    if (saved) {
      try {
        const cfg = JSON.parse(saved)
        if (cfg.temperature !== undefined) setTemperature(cfg.temperature)
        if (cfg.maxTokens !== undefined) setMaxTokens(cfg.maxTokens)
      } catch(e) {}
    }
  }, [])
  
  // Salvar config quando mudar
  React.useEffect(() => {
    localStorage.setItem('forge_config', JSON.stringify({ temperature, maxTokens }))
  }, [temperature, maxTokens])

  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    checkHealth()
    loadProjects()
    const interval = setInterval(checkHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const checkHealth = async () => {
    try {
      const res = await fetch('/api/health')
      if (!res.ok) {
        setStatus({ api: false, bridge: false })
        return
      }
      const text = await res.text()
      if (!text || text.startsWith('<')) {
        setStatus({ api: false, bridge: false })
        return
      }
      const data = JSON.parse(text)
      setStatus({ api: true, bridge: data.bridge_connected || false })
      setRuntime(data.runtime || runtime)
    } catch {
      setStatus({ api: false, bridge: false })
    }
  }

  const loadProjects = async () => {
    try {
      const res = await fetch('/api/projects')
      const data = await res.json()
      setProjects(data.projects || [])
    } catch {}
  }

  const connectWebSocket = (sid: string) => {
    if (wsRef.current) wsRef.current.close()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/sessions/${sid}`)
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'agent_message') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.content,
          timestamp: new Date().toISOString()
        }])
      } else if (data.type === 'tool_call') {
        setMessages(prev => [...prev, {
          role: 'tool',
          content: `[TOOL] ${data.tool}: ${JSON.stringify(data.args)}`,
          timestamp: new Date().toISOString(),
          toolName: data.tool
        }])
      } else if (data.type === 'tool_result') {
        const result = data.result || ''
        setMessages(prev => [...prev, {
          role: 'tool',
          content: `[OK] ${result.substring(0, 500)}${result.length > 500 ? '...' : ''}`,
          timestamp: new Date().toISOString()
        }])
      } else if (data.type === 'done') {
        setIsRunning(false)
      }
    }
    wsRef.current = ws
  }

  const sendMessage = async () => {
    if (!input.trim() || isRunning) return
    const userMsg: Message = {
      role: 'user', content: input, timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsRunning(true)

    try {
      const res = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, project_id: projects[0]?.id, temperature, max_tokens: maxTokens })
      })
      if (!res.ok) {
        throw new Error('Backend offline (status ' + res.status + ')')
      }
      const text = await res.text()
      if (!text || text.startsWith('<')) {
        throw new Error('Backend retornou HTML em vez de JSON')
      }
      const data = JSON.parse(text)
      if (data.session_id) {
        setSessionId(data.session_id)
        connectWebSocket(data.session_id)
      }
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: `Erro: ${err}`,
        timestamp: new Date().toISOString()
      }])
      setIsRunning(false)
    }
  }

  const stopAgent = async () => {
    if (sessionId) {
      await fetch(`/api/sessions/${sessionId}/cancel`, { method: 'POST' })
    }
    setIsRunning(false)
  }

  const executeTerminal = async () => {
    if (!terminalCmd.trim()) return
    setTerminalOutput(prev => [...prev, `$ ${terminalCmd}`])
    try {
      const res = await fetch('/api/bridge/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: terminalCmd })
      })
      const data = await res.json()
      setTerminalOutput(prev => [...prev, data.output || data.error || 'OK'])
    } catch (err) {
      setTerminalOutput(prev => [...prev, `Erro: ${err}`])
    }
    setTerminalCmd('')
  }

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'projects', label: 'Projetos', icon: Folder },
    { id: 'terminal', label: 'Terminal', icon: Terminal },
    { id: 'memory', label: 'Memoria', icon: Brain },
    { id: 'runtime', label: 'Runtime', icon: Cpu },
    { id: 'settings', label: 'Config', icon: Settings }
  ]

  return (
    <div className="flex h-screen bg-forge-bg text-neutral-200">
      <aside className="w-64 bg-forge-card border-r border-forge-border flex flex-col">
        <div className="p-4 border-b border-forge-border">
          <h1 className="text-xl font-bold bg-gradient-to-r from-orange-500 to-red-500 bg-clip-text text-transparent">
            [FORGE] ForgeAgent
          </h1>
          <p className="text-xs text-neutral-500 mt-1">AI Software Forge</p>
        </div>

        <nav className="flex-1 p-2">
          {tabs.map(tab => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg mb-1 transition-all ${
                  activeTab === tab.id
                    ? 'bg-orange-500/10 text-orange-400 border border-orange-500/30'
                    : 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200'
                }`}
              >
                <Icon size={18} />
                <span className="text-sm">{tab.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="p-3 border-t border-forge-border text-xs">
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-2 h-2 rounded-full ${status.api ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-neutral-400">API: {status.api ? 'Online' : 'Offline'}</span>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-2 h-2 rounded-full ${status.bridge ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-neutral-400">Bridge: {status.bridge ? 'Online' : 'Offline'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${runtime.mode === 'gpu' ? 'bg-green-500' : 'bg-yellow-500'}`} />
            <span className="text-neutral-400">
              {runtime.mode === 'gpu' ? 'GPU' : 'CPU'}: {runtime.model.substring(0, 25)}
            </span>
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col">
            <div className="p-4 border-b border-forge-border flex items-center justify-between">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <MessageSquare size={20} className="text-orange-400" />
                Chat com o Agente
              </h2>
              {isRunning ? (
                <button onClick={stopAgent} className="px-3 py-1 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 flex items-center gap-2 text-sm">
                  <Square size={14} /> Parar
                </button>
              ) : (
                <div className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg text-sm">
                  Pronto
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.length === 0 && (
                <div className="text-center text-neutral-500 mt-20">
                  <div className="text-5xl mb-4 font-bold text-orange-500">[FORGE]</div>
                  <h3 className="text-xl mb-2">Bem-vindo ao ForgeAgent</h3>
                  <p className="text-sm">Peca para criar projetos em C++, Java, Android, Linux, Windows...</p>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-3xl rounded-lg p-3 ${
                    msg.role === 'user' ? 'bg-orange-500/20 text-orange-100' :
                    msg.role === 'tool' ? 'bg-blue-500/10 text-blue-200 border border-blue-500/20' :
                    msg.role === 'system' ? 'bg-red-500/10 text-red-200' :
                    'bg-neutral-800 text-neutral-200'
                  }`}>
                    <pre className="whitespace-pre text-sm terminal-font overflow-x-auto max-w-full" style={{wordBreak: "break-word"}}>{msg.content}</pre>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-forge-border">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendMessage()}
                  placeholder="Descreva o que quer criar..."
                  disabled={isRunning}
                  className="flex-1 bg-neutral-900 border border-forge-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-orange-500 disabled:opacity-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={isRunning || !input.trim()}
                  className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 flex items-center gap-2"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'projects' && (
          <div className="flex-1 overflow-y-auto p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Folder size={20} className="text-orange-400" />
              Projetos
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map(p => (
                <div key={p.id} className="bg-forge-card border border-forge-border rounded-lg p-4 hover:border-orange-500/50 transition-all">
                  <h3 className="font-semibold mb-2">{p.name}</h3>
                  <div className="text-xs text-neutral-500 space-y-1">
                    <div>Linguagem: {p.language}</div>
                    <div>Tarefas: {p.tasks_count}</div>
                    <div>Criado: {new Date(p.created_at).toLocaleDateString()}</div>
                  </div>
                </div>
              ))}
              {projects.length === 0 && (
                <div className="col-span-full text-center text-neutral-500 py-12">
                  Nenhum projeto ainda. Peca ao agente para criar um!
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'terminal' && (
          <div className="flex-1 flex flex-col">
            <div className="p-4 border-b border-forge-border">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Terminal size={20} className="text-orange-400" />
                Terminal Remoto
              </h2>
            </div>
            <div className="flex-1 bg-black p-4 overflow-y-auto terminal-font text-sm">
              {terminalOutput.map((line, i) => (
                <div key={i} className={line.startsWith('$') ? 'text-green-400' : line.startsWith('Erro') ? 'text-red-400' : 'text-neutral-300'}>
                  {line}
                </div>
              ))}
            </div>
            <div className="p-3 border-t border-forge-border flex gap-2">
              <input
                value={terminalCmd}
                onChange={e => setTerminalCmd(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && executeTerminal()}
                placeholder="$ digite um comando..."
                className="flex-1 bg-neutral-900 border border-forge-border rounded px-3 py-2 terminal-font text-sm"
              />
              <button onClick={executeTerminal} className="px-4 py-2 bg-orange-500 rounded hover:bg-orange-600">
                Executar
              </button>
            </div>
          </div>
        )}

        {activeTab === 'memory' && (
          <div className="flex-1 overflow-y-auto p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Brain size={20} className="text-orange-400" />
              Memoria do Agente
            </h2>
            <div className="bg-forge-card border border-forge-border rounded-lg p-4">
              <p className="text-sm text-neutral-400 mb-4">
                Persistida automaticamente no Google Drive
              </p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between p-2 bg-neutral-900 rounded">
                  <span>Historico de sessoes</span>
                  <span className="text-orange-400">Drive/sessions/</span>
                </div>
                <div className="flex justify-between p-2 bg-neutral-900 rounded">
                  <span>Memoria longo prazo</span>
                  <span className="text-orange-400">Drive/memory/</span>
                </div>
                <div className="flex justify-between p-2 bg-neutral-900 rounded">
                  <span>Projetos</span>
                  <span className="text-orange-400">Drive/projects/</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'runtime' && (
          <div className="flex-1 overflow-y-auto p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Cpu size={20} className="text-orange-400" />
              Runtime do Modelo
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-forge-card border border-forge-border rounded-lg p-4">
                <h3 className="font-semibold mb-3 text-orange-400">Status</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-400">Modo:</span>
                    <span className={runtime.mode === 'gpu' ? 'text-green-400' : 'text-yellow-400'}>
                      {runtime.mode.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-400">Backend:</span>
                    <span>{runtime.backend}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-400">Modelo:</span>
                    <span className="text-xs">{runtime.model}</span>
                  </div>
                  {runtime.gpu_name && (
                    <div className="flex justify-between">
                      <span className="text-neutral-400">GPU:</span>
                      <span className="text-green-400">{runtime.gpu_name}</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="bg-forge-card border border-forge-border rounded-lg p-4">
                <h3 className="font-semibold mb-3 text-orange-400">Capacidades</h3>
                <div className="space-y-1 text-sm">
                  <div>[OK] C/C++ (GCC, Clang, CMake)</div>
                  <div>[OK] Java (Maven, Gradle)</div>
                  <div>[OK] Android (Gradle, SDK)</div>
                  <div>[OK] Linux (Bash, Make, systemd)</div>
                  <div>[OK] Windows (PowerShell, batch)</div>
                  <div>[OK] Python, Node.js</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="flex-1 overflow-y-auto p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Settings size={20} className="text-orange-400" />
              Configuracoes
            </h2>
            <div className="bg-forge-card border border-forge-border rounded-lg p-4 space-y-4">
              <div>
                <label className="text-sm text-neutral-400 block mb-1">Modelo LLM</label>
                <select className="w-full bg-neutral-900 border border-forge-border rounded px-3 py-2">
                  <option>Gemini 1.5 Flash (Cloud) - 1M tokens</option>
                  <option>Gemini 1.5 Pro (Cloud) - 2M tokens</option>
                  <option>Gemini 2.0 Flash (Cloud) - Ultra rápido</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-neutral-400 block mb-1">Temperatura</label>
                <input type="range" min="0" max="1" step="0.1" value={temperature} onChange={e => setTemperature(parseFloat(e.target.value))} className="w-full" /><span className="text-xs text-neutral-400 ml-2">{temperature}</span>
              </div>
              <div>
                <label className="text-sm text-neutral-400 block mb-1">Max Tokens</label>
                <input type="number" value={maxTokens} onChange={e => setMaxTokens(parseInt(e.target.value) || 2048)} className="w-full bg-neutral-900 border border-forge-border rounded px-3 py-2" />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
