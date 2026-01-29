import { useEffect, useState } from 'react'

const stages = [
  { id: 'idea', label: 'Idea' },
  { id: 'related_work', label: 'Related Work' },
  { id: 'method', label: 'Method' },
  { id: 'experiments', label: 'Experiments' },
  { id: 'results', label: 'Results' },
  { id: 'draft', label: 'Draft' },
  { id: 'submission', label: 'Submission' }
]

type Project = {
  id: number
  name: string
  description: string
  created_at: string
}

type Stage = {
  stage_id: string
  completed: boolean
  completed_at?: string
}

type StageFile = {
  id: number
  filename: string
  uploaded_at: string
  stored_path: string
}

type ProjectDetail = {
  project: Project
  stages: Stage[]
  files: StageFile[]
}

function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [activeProject, setActiveProject] = useState<ProjectDetail | null>(null)
  const [projectName, setProjectName] = useState('')
  const [projectDesc, setProjectDesc] = useState('')
  const [selectedStage, setSelectedStage] = useState('idea')
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  const loadProjects = async () => {
    const res = await fetch('/api/projects')
    setProjects(await res.json())
  }

  const loadProjectDetail = async (projectId: number) => {
    const res = await fetch(`/api/projects/${projectId}`)
    setActiveProject(await res.json())
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const createProject = async () => {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: projectName, description: projectDesc })
    })
    const project = await res.json()
    setProjects((prev) => [...prev, project])
    setProjectName('')
    setProjectDesc('')
    loadProjectDetail(project.id)
  }

  const markComplete = async (stageId: string) => {
    if (!activeProject) return
    await fetch(`/api/projects/${activeProject.project.id}/stages/${stageId}/complete`, {
      method: 'POST'
    })
    loadProjectDetail(activeProject.project.id)
  }

  const resetStage = async (stageId: string) => {
    if (!activeProject) return
    await fetch(`/api/projects/${activeProject.project.id}/stages/${stageId}/reset`, {
      method: 'POST'
    })
    loadProjectDetail(activeProject.project.id)
  }

  const uploadStageFile = async () => {
    if (!activeProject || !uploadFile) return
    const form = new FormData()
    form.append('file', uploadFile)
    await fetch(`/api/projects/${activeProject.project.id}/stages/${selectedStage}/upload`, {
      method: 'POST',
      body: form
    })
    setUploadFile(null)
    loadProjectDetail(activeProject.project.id)
  }

  const stageFiles = activeProject?.files.filter((file) => file.stored_path.includes(`/${selectedStage}/`)) ?? []
  const stageState = activeProject?.stages.find((stage) => stage.stage_id === selectedStage)

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>Research Tracker</h2>
        <div className="card" style={{ background: '#1e293b' }}>
          <h4>Create Project</h4>
          <label>Name</label>
          <input value={projectName} onChange={(e) => setProjectName(e.target.value)} />
          <label>Description</label>
          <textarea value={projectDesc} onChange={(e) => setProjectDesc(e.target.value)} />
          <button onClick={createProject} style={{ marginTop: 8 }}>
            Create
          </button>
        </div>
        <div className="card" style={{ background: '#1e293b' }}>
          <h4>Projects</h4>
          {projects.map((project) => (
            <div key={project.id} style={{ marginBottom: 8 }}>
              <button onClick={() => loadProjectDetail(project.id)}>{project.name}</button>
            </div>
          ))}
        </div>
      </aside>
      <main className="content">
        <div className="card">
          <h3>{activeProject ? activeProject.project.name : 'Select a project'}</h3>
          <p>{activeProject?.project.description}</p>
        </div>
        <div className="card">
          <h4>Stages</h4>
          {stages.map((stage) => {
            const stageInfo = activeProject?.stages.find((item) => item.stage_id === stage.id)
            return (
              <div className="stage" key={stage.id}>
                <div>
                  <strong>{stage.label}</strong>
                  {stageInfo?.completed_at && (
                    <div style={{ fontSize: 12, color: '#64748b' }}>
                      Completed: {new Date(stageInfo.completed_at).toLocaleString()}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span className={`pill ${stageInfo?.completed ? 'done' : 'todo'}`}>
                    {stageInfo?.completed ? 'Done' : 'Open'}
                  </span>
                  <button onClick={() => setSelectedStage(stage.id)}>Open</button>
                </div>
              </div>
            )
          })}
        </div>
        {activeProject && (
          <div className="card">
            <h4>Stage: {stages.find((stage) => stage.id === selectedStage)?.label}</h4>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <button onClick={() => markComplete(selectedStage)}>Mark Complete</button>
              <button onClick={() => resetStage(selectedStage)}>Reset</button>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>Upload file (PDF, CSV, DOC, etc.)</label>
              <input type="file" onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)} />
              <button onClick={uploadStageFile} style={{ marginTop: 8 }}>
                Upload
              </button>
            </div>
            <div>
              <h5>Files</h5>
              {stageFiles.length === 0 && <div>No files yet.</div>}
              <ul>
                {stageFiles.map((file) => (
                  <li key={file.id}>
                    <a href={`/api/files/${file.id}`} target="_blank" rel="noreferrer">
                      {file.filename}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
