import { useEffect, useMemo, useState } from 'react'

const steps = ['part1', 'part2', 'part3', 'part4', 'final']

type Project = {
  id: number
  name: string
  description: string
  settings?: Record<string, unknown>
}

type StepRun = {
  id: number
  created_at: string
  output_json: Record<string, unknown>
  provider?: string
  model?: string
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
  const [clusterHost, setClusterHost] = useState('')
  const [clusterPort, setClusterPort] = useState(22)
  const [clusterUser, setClusterUser] = useState('')
  const [clusterKeyPath, setClusterKeyPath] = useState('')
  const [clusterRemoteDir, setClusterRemoteDir] = useState('')
  const [clusterPartition, setClusterPartition] = useState('')
  const [clusterTime, setClusterTime] = useState('')
  const [clusterMem, setClusterMem] = useState('')
  const [clusterCpus, setClusterCpus] = useState('')
  const [clusterGres, setClusterGres] = useState('')
  const [clusterEnvInit, setClusterEnvInit] = useState('')
  const [clusterUploads, setClusterUploads] = useState('')
  const [clusterDownloads, setClusterDownloads] = useState('')
  const [executionId, setExecutionId] = useState<number | null>(null)
  const [ingestFile, setIngestFile] = useState<File | null>(null)
  const [ingestLabel, setIngestLabel] = useState('')
  const [ingestArtifacts, setIngestArtifacts] = useState<string[]>([])
  const [ingestStatus, setIngestStatus] = useState('')
  const [includeUnverified, setIncludeUnverified] = useState(false)
  const [citationSummary, setCitationSummary] = useState<{verified: number; unverified: number}>({
    verified: 0,
    unverified: 0
  })
  const [unverifiedTitles, setUnverifiedTitles] = useState<string[]>([])
  const [editorMode, setEditorMode] = useState<'json' | 'markdown'>('json')
  const [isEditing, setIsEditing] = useState(false)
  const [lockedSteps, setLockedSteps] = useState<Record<string, boolean>>({})
  const [artifactTab, setArtifactTab] = useState<'markdown' | 'json' | 'citations' | 'latex' | 'pdf'>(
    'markdown'
  )
  const [artifactContent, setArtifactContent] = useState('')
  const [selectedArtifactPath, setSelectedArtifactPath] = useState('')
  const [pdfWarning, setPdfWarning] = useState('')

  const resultsBlocked = selectedStep === 'final' && !artifacts.includes('part4/metrics.json')
  const stepLocked = Boolean(lockedSteps[selectedStep])
  const canRun = useMemo(
    () => activeProject !== null && !resultsBlocked && !stepLocked,
    [activeProject, resultsBlocked, stepLocked]
  )

  useEffect(() => {
    fetch('/api/projects')
      .then((res) => res.json())
      .then(setProjects)
      .catch(() => setProjects([]))
  }, [])

  useEffect(() => {
    if (!activeProject) return
    fetch(`/api/projects/${activeProject.id}`)
      .then((res) => res.json())
      .then((data) => {
        setIncludeUnverified(Boolean(data.settings?.include_unverified_citations))
      })
    fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/runs`)
      .then((res) => res.json())
      .then(setRuns)
      .catch(() => setRuns([]))
    fetch(`/api/projects/${activeProject.id}/artifacts`)
      .then((res) => res.json())
      .then((data) => setArtifacts(data.files ?? []))
      .catch(() => setArtifacts([]))
    fetch(`/api/projects/${activeProject.id}/steps/part1/runs`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.length) {
          setCitationSummary({ verified: 0, unverified: 0 })
          setUnverifiedTitles([])
          return
        }
        const latest = data[0]?.output_json?.related_work_candidates ?? []
        const verified = latest.filter((item: { status?: string }) => item.status === 'verified')
        const unverified = latest.filter((item: { status?: string }) => item.status !== 'verified')
        setCitationSummary({ verified: verified.length, unverified: unverified.length })
        setUnverifiedTitles(unverified.map((item: { title?: string }) => item.title || 'Untitled'))
      })
      .catch(() => {
        setCitationSummary({ verified: 0, unverified: 0 })
        setUnverifiedTitles([])
      })
  }, [activeProject, selectedStep])

  useEffect(() => {
    if (!activeProject || !selectedArtifactPath) return
    fetch(`/api/projects/${activeProject.id}/artifacts/content?path=${selectedArtifactPath}`)
      .then((res) => res.text())
      .then(setArtifactContent)
      .catch(() => setArtifactContent('Unable to load artifact'))
  }, [activeProject, selectedArtifactPath])

  useEffect(() => {
    if (!activeProject) return
    const pdf = artifacts.find((file) => file.endsWith('.pdf'))
    if (pdf) {
      setSelectedArtifactPath(pdf)
    }
  }, [activeProject, artifacts])

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

  const saveEdit = async () => {
    if (!activeProject) return
    let payload: Record<string, unknown>
    if (editorMode === 'json') {
      payload = JSON.parse(stepOutput || '{}')
    } else {
      payload = { markdown: stepOutput }
    }
    await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ output: payload, notes: 'manual edit' })
    })
    setIsEditing(false)
    const runsRes = await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/runs`)
    setRuns(await runsRes.json())
  }

  const approveStep = async () => {
    if (!activeProject) return
    await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/approve`, { method: 'POST' })
    setLockedSteps((prev) => ({ ...prev, [selectedStep]: true }))
  }

  const unlockStep = async () => {
    if (!activeProject) return
    await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/unlock`, { method: 'POST' })
    setLockedSteps((prev) => ({ ...prev, [selectedStep]: false }))
  }

  const loadDiff = async () => {
    if (!activeProject || !selectedRuns.a || !selectedRuns.b) return
    const res = await fetch(
      `/api/projects/${activeProject.id}/steps/${selectedStep}/diff?run_a=${selectedRuns.a}&run_b=${selectedRuns.b}`
    )
    const data = await res.json()
    setDiff(data.diff || [])
  }

  const loadRunOutput = (run: StepRun) => {
    setStepOutput(JSON.stringify(run.output_json, null, 2))
    setIsEditing(false)
  }

  const rollbackRun = async (run: StepRun) => {
    if (!activeProject) return
    await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ output: run.output_json, notes: `rollback to ${run.id}` })
    })
    const runsRes = await fetch(`/api/projects/${activeProject.id}/steps/${selectedStep}/runs`)
    setRuns(await runsRes.json())
  }

  const downloadLatex = () => {
    if (!activeProject) return
    window.location.href = `/api/projects/${activeProject.id}/export/latex`
  }

  const downloadPdf = async () => {
    if (!activeProject) return
    setPdfWarning('')
    const res = await fetch(`/api/projects/${activeProject.id}/export/pdf`)
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/pdf')) {
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'main.pdf'
      link.click()
      window.URL.revokeObjectURL(url)
      return
    }
    const data = await res.json()
    if (data.warning) {
      setPdfWarning(data.warning)
    }
  }

  const planExecution = async () => {
    if (!activeProject) return
    const parsePairs = (value: string) =>
      value
        .split('\n')
        .map((line) => line.split('|').map((part) => part.trim()))
        .filter((parts) => parts.length === 2 && parts[0] && parts[1])
        .map(([local, remote]) => ({ local, remote }))
    const res = await fetch(`/api/projects/${activeProject.id}/executions/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        runner,
        commands: commands.split('\n').filter(Boolean),
        context: {
          cluster_profile: {
            host: clusterHost,
            port: clusterPort,
            username: clusterUser,
            key_path: clusterKeyPath,
            remote_base_dir: clusterRemoteDir,
            defaults: {
              partition: clusterPartition,
              time: clusterTime,
              mem: clusterMem,
              cpus: clusterCpus,
              gres: clusterGres
            },
            env_init_commands: clusterEnvInit
              .split('\n')
              .map((line) => line.trim())
              .filter(Boolean)
          },
          staging: {
            upload: parsePairs(clusterUploads),
            download: parsePairs(clusterDownloads)
          }
        }
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
    setExecutionId(data.execution_id)
    const logsRes = await fetch(`/api/projects/${activeProject.id}/executions/${data.execution_id}/logs`)
    const logsData = await logsRes.json()
    setExecLogs(`${logsData.stdout}\\n${logsData.stderr}`)
  }

  const refreshExecutionStatus = async () => {
    if (!activeProject || !executionId) return
    const res = await fetch(
      `/api/projects/${activeProject.id}/executions/${executionId}/status`
    )
    const data = await res.json()
    setExecStatus(`${data.status} (exit ${data.exit_code ?? 'n/a'})`)
  }

  const cancelExecution = async () => {
    if (!activeProject || !executionId) return
    await fetch(`/api/projects/${activeProject.id}/executions/${executionId}/cancel`, {
      method: 'POST'
    })
    setExecStatus('cancelled')
  }

  const collectExecution = async () => {
    if (!activeProject || !executionId) return
    const res = await fetch(`/api/projects/${activeProject.id}/executions/${executionId}/collect`, {
      method: 'POST'
    })
    const data = await res.json()
    setExecStatus(data.status || execStatus)
    const artifactsRes = await fetch(`/api/projects/${activeProject.id}/artifacts`)
    const artifactsData = await artifactsRes.json()
    setArtifacts(artifactsData.files ?? [])
    if (data.files) {
      setExecLogs(`${execLogs}\\nCollected: ${data.files.join(', ')}`)
    }
  }

  const ingestMetrics = async () => {
    if (!activeProject || !ingestFile) return
    const formData = new FormData()
    formData.append('file', ingestFile)
    if (ingestLabel) {
      formData.append('label', ingestLabel)
    }
    const res = await fetch(`/api/projects/${activeProject.id}/ingest`, {
      method: 'POST',
      body: formData
    })
    if (!res.ok) {
      const error = await res.json()
      setIngestStatus(error.detail || 'Ingestion failed')
      return
    }
    const data = await res.json()
    setIngestArtifacts(data.artifacts || [])
    setIngestStatus('Ingestion complete')
    const artifactsRes = await fetch(`/api/projects/${activeProject.id}/artifacts`)
    const artifactsData = await artifactsRes.json()
    setArtifacts(artifactsData.files ?? [])
  }

  const updateIncludeUnverified = async (value: boolean) => {
    if (!activeProject) return
    setIncludeUnverified(value)
    await fetch(`/api/projects/${activeProject.id}/settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ settings: { include_unverified_citations: value } })
    })
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
          <label style={{ marginTop: 8 }}>Include unverified citations</label>
          <input
            type="checkbox"
            checked={includeUnverified}
            onChange={(e) => updateIncludeUnverified(e.target.checked)}
          />
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
              <button onClick={runStep} disabled={!canRun}>
                {resultsBlocked ? 'Run (blocked)' : 'Run'}
              </button>
              <button onClick={runStep} disabled={!canRun}>
                Re-run
              </button>
              <button onClick={approveStep}>Approve</button>
              <button onClick={unlockStep}>Unlock</button>
            </div>
            {stepLocked && <div style={{ marginTop: 8 }}>Status: Locked</div>}
          </div>
          <div className="card">
            <h4>Output</h4>
            <label>Editor Mode</label>
            <select
              value={editorMode}
              onChange={(e) => setEditorMode(e.target.value as 'json' | 'markdown')}
            >
              <option value="json">JSON</option>
              <option value="markdown">Markdown</option>
            </select>
            <textarea value={stepOutput} onChange={(e) => setStepOutput(e.target.value)} rows={16} />
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button onClick={() => setIsEditing(true)}>Edit</button>
              <button onClick={saveEdit} disabled={!isEditing}>
                Save
              </button>
            </div>
          </div>
        </div>
        <div className="grid">
          <div className="card">
            <h4>Run History</h4>
            <ul>
              {runs.map((run) => (
                <li key={run.id}>
                  <strong>Run {run.id}</strong> — {new Date(run.created_at).toLocaleString()} (
                  {run.provider}/{run.model})
                  <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                    <button onClick={() => loadRunOutput(run)}>Load</button>
                    <button onClick={() => rollbackRun(run)}>Rollback</button>
                  </div>
                </li>
              ))}
            </ul>
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
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <button onClick={downloadLatex}>Download LaTeX (.zip)</button>
              <button onClick={downloadPdf}>Download PDF</button>
            </div>
            {pdfWarning && (
              <div style={{ marginBottom: 8, color: '#b45309' }}>
                PDF export warning: {pdfWarning}
              </div>
            )}
            <div className="tabs">
              <button className="tab" onClick={() => setArtifactTab('markdown')}>Markdown</button>
              <button className="tab" onClick={() => setArtifactTab('json')}>JSON</button>
              <button className="tab" onClick={() => setArtifactTab('citations')}>Citation Status</button>
              <button className="tab" onClick={() => setArtifactTab('latex')}>LaTeX</button>
              <button className="tab" onClick={() => setArtifactTab('pdf')}>PDF</button>
            </div>
            <select
              value={selectedArtifactPath}
              onChange={(e) => setSelectedArtifactPath(e.target.value)}
            >
              <option value="">Select artifact</option>
              {artifacts.map((file) => (
                <option key={file} value={file}>{file}</option>
              ))}
            </select>
            {artifactTab === 'markdown' && <pre>{artifactContent}</pre>}
            {artifactTab === 'json' && <pre>{artifactContent}</pre>}
            {artifactTab === 'latex' && <pre>{artifactContent}</pre>}
            {artifactTab === 'citations' && (
              <>
                <div>Verified: {citationSummary.verified}</div>
                <div>Unverified: {citationSummary.unverified}</div>
                {unverifiedTitles.length > 0 && (
                  <ul>
                    {unverifiedTitles.map((title) => (
                      <li key={title}>{title} (UNVERIFIED)</li>
                    ))}
                  </ul>
                )}
              </>
            )}
            {artifactTab === 'pdf' && selectedArtifactPath.endsWith('.pdf') && (
              <iframe
                title="pdf-preview"
                src={`/api/projects/${activeProject?.id}/artifacts/file?path=${selectedArtifactPath}`}
                style={{ width: '100%', height: 400, border: '1px solid #e2e8f0' }}
              />
            )}
          </div>
        </div>
        {selectedStep === 'part4' && (
          <div className="card">
            <h4>Part 4 Ingestion</h4>
            <label>Upload CSV/JSON</label>
            <input
              type="file"
              accept=".csv,.json"
              onChange={(e) => setIngestFile(e.target.files?.[0] ?? null)}
            />
            <label>Label (optional)</label>
            <input value={ingestLabel} onChange={(e) => setIngestLabel(e.target.value)} />
            <button style={{ marginTop: 8 }} onClick={ingestMetrics}>
              Ingest
            </button>
            <div style={{ marginTop: 8 }}>{ingestStatus}</div>
            <ul>
              {ingestArtifacts.map((artifact) => (
                <li key={artifact}>{artifact}</li>
              ))}
            </ul>
          </div>
        )}
        {selectedStep === 'final' && !artifacts.includes('part4/metrics.json') && (
          <div className="card" style={{ border: '1px solid #dc2626' }}>
            <h4>Results blocked</h4>
            <p>Metrics not found. Run Part 4 ingestion to enable Results.</p>
            <button onClick={() => setSelectedStep('part4')}>Go to Part 4</button>
          </div>
        )}
        <div className="card">
          <h4>Execution (Plan → Approve → Run)</h4>
          {selectedStep === 'part4' && (
            <>
              <h5>Cluster Profile</h5>
              <label>Host</label>
              <input value={clusterHost} onChange={(e) => setClusterHost(e.target.value)} />
              <label>Port</label>
              <input
                type="number"
                value={clusterPort}
                onChange={(e) => setClusterPort(Number(e.target.value))}
              />
              <label>Username</label>
              <input value={clusterUser} onChange={(e) => setClusterUser(e.target.value)} />
              <label>SSH Key Path</label>
              <input value={clusterKeyPath} onChange={(e) => setClusterKeyPath(e.target.value)} />
              <label>Remote Base Dir</label>
              <input
                value={clusterRemoteDir}
                onChange={(e) => setClusterRemoteDir(e.target.value)}
              />
              <label>Partition</label>
              <input
                value={clusterPartition}
                onChange={(e) => setClusterPartition(e.target.value)}
              />
              <label>Time</label>
              <input value={clusterTime} onChange={(e) => setClusterTime(e.target.value)} />
              <label>Memory</label>
              <input value={clusterMem} onChange={(e) => setClusterMem(e.target.value)} />
              <label>CPUs</label>
              <input value={clusterCpus} onChange={(e) => setClusterCpus(e.target.value)} />
              <label>GRES</label>
              <input value={clusterGres} onChange={(e) => setClusterGres(e.target.value)} />
              <label>Env Init Commands (one per line)</label>
              <textarea
                value={clusterEnvInit}
                onChange={(e) => setClusterEnvInit(e.target.value)}
                rows={3}
              />
              <label>Upload Mappings (local|remote per line)</label>
              <textarea
                value={clusterUploads}
                onChange={(e) => setClusterUploads(e.target.value)}
                rows={3}
              />
              <label>Download Mappings (local|remote per line)</label>
              <textarea
                value={clusterDownloads}
                onChange={(e) => setClusterDownloads(e.target.value)}
                rows={3}
              />
            </>
          )}
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
            <button onClick={refreshExecutionStatus}>Status</button>
            <button onClick={cancelExecution}>Cancel</button>
            <button onClick={collectExecution}>Collect</button>
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
