import { useEffect, useMemo, useState } from 'react'

const steps = ['part1', 'part2', 'part3', 'part4', 'final']

type Project = {
  id: number
  name: string
  description: string
}

type StepRun = {
  id: number
  created_at: string
  output_json: Record<string, unknown>
}

function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [activeProject, setActiveProject] = useState<Project | null>(null)
  const [projectName, setProjectName] = useState('')
  const [projectDesc, setProjectDesc] = useState('')
  const [selectedStep, setSelectedStep] = useState('part1')
  const [provider, setProvider] = useState('gemini')
  const [model, setModel] = useState('gemini-1.5-pro')
  const [temperature, setTemperature] = useState(0.2)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [inputs, setInputs] = useState('{}')
  const [stepOutput, setStepOutput] = useState('{}')
  const [runs, setRuns] = useState<StepRun[]>([])
  const [artifacts, setArtifacts] = useState<string[]>([])
  const [diff, setDiff] = useState<string[]>([])
  const [selectedRuns, setSelectedRuns] = useState<{a?: number; b?: number}>({})
  const [runner, setRunner] = useState('local')
  const [commands, setCommands] = useState('echo \"hello\"')
  const [planId, setPlanId] = useState<number | null>(null)
  const [planWarnings, setPlanWarnings] = useState<string[]>([])
  const [execStatus, setExecStatus] = useState<string>('')
  const [execLogs, setExecLogs] = useState<string>('')

  const canRun = useMemo(() => activeProject !== null, [activeProject])

  useEffect(() => {
    fetch('/api/projects')
      .then((res) => res.json())
      .then(setProjects)
      .catch(() => setProjects([]))
  }, [])

  useEffect(() => {
    if (!activeProject) return
    fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/runs`)
      .then((res) => res.json())
      .then(setRuns)
      .catch(() => setRuns([]))
    fetch(`/api/projects/${activeProject.id}/artifacts`)
      .then((res) => res.json())
      .then((data) => setArtifacts(data.files ?? []))
      .catch(() => setArtifacts([]))
  }, [activeProject, selectedStep])

  const createProject = async () => {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: projectName, description: projectDesc })
    })
    const data = await res.json()
    setProjects((prev) => [...prev, data])
    setActiveProject(data)
    setProjectName('')
    setProjectDesc('')
  }

  const runStep = async () => {
    if (!activeProject) return
    const res = await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider,
        model,
        temperature,
        max_tokens: maxTokens,
        inputs: JSON.parse(inputs || '{}')
      })
    })
    const data = await res.json()
    setStepOutput(JSON.stringify(data.output, null, 2))
    const runsRes = await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/runs`)
    setRuns(await runsRes.json())
  }

  const approveStep = async () => {
    if (!activeProject) return
    await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/approve`, { method: 'POST' })
  }

  const unlockStep = async () => {
    if (!activeProject) return
    await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/unlock`, { method: 'POST' })
  }

  const loadDiff = async () => {
    if (!activeProject || !selectedRuns.a || !selectedRuns.b) return
    const res = await fetch(
      `/api/projects/${activeProject.id}/steps/${selectedStep}/diff?run_a=${selectedRuns.a}&run_b=${selectedRuns.b}`
    )
    const data = await res.json()
    setDiff(data.diff || [])
  }

  const planExecution = async () => {
    if (!activeProject) return
    const res = await fetch(`/api/projects/${activeProject.id}/executions/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        runner,
        commands: commands.split('\n').filter(Boolean),
        context: {}
      })
    })
    const data = await res.json()
    setPlanId(data.plan_id)
    setPlanWarnings(data.warnings || [])
  }

  const approvePlan = async () => {
    if (!activeProject || !planId) return
    await fetch(`/api/projects/${activeProject.id}/executions/plan/${planId}/approve`, {
      method: 'POST'
    })
  }

  const runExecution = async () => {
    if (!activeProject || !planId) return
    const res = await fetch(`/api/projects/${activeProject.id}/executions/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan_id: planId })
    })
    const data = await res.json()
    setExecStatus(`${data.status} (exit ${data.exit_code ?? 'n/a'})`)
    const logsRes = await fetch(`/api/projects/${activeProject.id}/executions/${data.execution_id}/logs`)
    const logsData = await logsRes.json()
    setExecLogs(`${logsData.stdout}\\n${logsData.stderr}`)
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>Research Pipeline Studio</h2>
        <div className="card" style={{ background: '#1e293b' }}>
          <h4>Create Project</h4>
          <label>Name</label>
          <input value={projectName} onChange={(e) => setProjectName(e.target.value)} />
          <label>Description</label>
          <textarea value={projectDesc} onChange={(e) => setProjectDesc(e.target.value)} />
          <button onClick={createProject} style={{ marginTop: 8 }}>Create</button>
        </div>
        <div className="card" style={{ background: '#1e293b' }}>
          <h4>Projects</h4>
          {projects.map((project) => (
            <div key={project.id} style={{ marginBottom: 8 }}>
              <button onClick={() => setActiveProject(project)}>{project.name}</button>
            </div>
          ))}
        </div>
      </aside>
      <main className="content">
        <div className="card">
          <h3>{activeProject ? activeProject.name : 'Select a Project'}</h3>
          <div className="stepper">
            {steps.map((step) => (
              <span
                key={step}
                className="step"
                style={{ background: selectedStep === step ? '#93c5fd' : '#e2e8f0' }}
                onClick={() => setSelectedStep(step)}
              >
                {step.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
        <div className="grid">
          <div className="card">
            <h4>Step Controls</h4>
            <label>Provider</label>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="gemini">Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
            <label>Model</label>
            <input value={model} onChange={(e) => setModel(e.target.value)} />
            <label>Temperature</label>
            <input
              type="number"
              value={temperature}
              step={0.1}
              onChange={(e) => setTemperature(Number(e.target.value))}
            />
            <label>Max Tokens</label>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
            />
            <label>Inputs (JSON)</label>
            <textarea value={inputs} onChange={(e) => setInputs(e.target.value)} rows={6} />
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button onClick={runStep} disabled={!canRun}>Run</button>
              <button onClick={approveStep}>Approve</button>
              <button onClick={unlockStep}>Unlock</button>
            </div>
          </div>
          <div className="card">
            <h4>Output</h4>
            <textarea value={stepOutput} onChange={(e) => setStepOutput(e.target.value)} rows={16} />
          </div>
        </div>
        <div className="grid">
          <div className="card">
            <h4>Run History</h4>
            <select onChange={(e) => setSelectedRuns((prev) => ({ ...prev, a: Number(e.target.value) }))}>
              <option>Select Run A</option>
              {runs.map((run) => (
                <option key={run.id} value={run.id}>{run.id}</option>
              ))}
            </select>
            <select onChange={(e) => setSelectedRuns((prev) => ({ ...prev, b: Number(e.target.value) }))}>
              <option>Select Run B</option>
              {runs.map((run) => (
                <option key={run.id} value={run.id}>{run.id}</option>
              ))}
            </select>
            <button onClick={loadDiff}>Load Diff</button>
            <pre>{diff.join('\n')}</pre>
          </div>
          <div className="card">
            <h4>Artifacts</h4>
            <ul>
              {artifacts.map((file) => (
                <li key={file}>{file}</li>
              ))}
            </ul>
          </div>
        </div>
        <div className="card">
          <h4>Execution (Plan → Approve → Run)</h4>
          <label>Runner</label>
          <select value={runner} onChange={(e) => setRunner(e.target.value)}>
            <option value="local">Local</option>
            <option value="ssh">SSH</option>
            <option value="slurm">Slurm</option>
          </select>
          <label>Commands (one per line)</label>
          <textarea value={commands} onChange={(e) => setCommands(e.target.value)} rows={4} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button onClick={planExecution}>Plan</button>
            <button onClick={approvePlan}>Approve</button>
            <button onClick={runExecution}>Approve &amp; Run</button>
          </div>
          {planWarnings.length > 0 && (
            <div style={{ marginTop: 8, color: '#b91c1c' }}>
              Warnings: {planWarnings.join(', ')}
            </div>
          )}
          <div style={{ marginTop: 8 }}>Status: {execStatus}</div>
          <pre>{execLogs}</pre>
        </div>
      </main>
    </div>
  )
}

export default App
