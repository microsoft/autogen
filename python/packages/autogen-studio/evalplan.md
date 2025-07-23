# AutoGen Studio Evaluation System - UI/API Design Plan

## 🎯 Overview

This document outlines the comprehensive design for AutoGen Studio's evaluation system UI and API, providing a complete user experience for creating, managing, and analyzing LLM/agent evaluations.

## 📊 Current Architecture Analysis

### ✅ Existing Patterns
- **Manager/Sidebar Pattern**: Workflows, Teams, MCP all use `Manager + Sidebar + Builder`
- **API Structure**: RESTful with `BaseAPI` class, user-scoped endpoints
- **State Management**: React hooks + localStorage for persistence
- **UI Components**: Ant Design + Lucide icons, collapsible sidebars

### 🏗️ Backend Capabilities
- **Batch-first runners** with parallel processing
- **Isolated team evaluation** preventing state contamination
- **LLM-based judges** with multi-dimensional scoring
- **Orchestrator** for managing evaluation lifecycle
- **Database persistence** for tasks, criteria, runs, and results

## 🚀 Proposed User Experience Flow

### 1. 📋 Task Management (`/evaluations/tasks`)

**Features:**
- **Create Task Sets**
  - Manual task creation (text input + expected output)
  - CSV/JSON upload (batch import)
  - Template library (common eval patterns)
  - Multi-modal support (text + images)
- **Task Set Library**
  - Browse existing task sets
  - Filter by category/tags
  - Preview tasks
  - Clone/duplicate sets

**User Journey:**
```
User creates task set → Adds individual tasks or uploads batch → 
Organizes with tags/categories → Saves for reuse
```

### 2. ⚙️ Evaluation Configuration (`/evaluations/configs`)

**Features:**
- **Runner Configuration**
  - Model runners (select model, parameters)
  - Team runners (select team, max turns)
  - Runner comparison setup
- **Judge Configuration**
  - Criteria definition (accuracy, relevance, etc.)
  - Custom prompts per dimension
  - Scoring scales (0-10, 0-100, etc.)
  - Judge model selection
- **Evaluation Templates**
  - Pre-built templates (QA, summarization, etc.)
  - Save custom configs as templates
  - Share templates with team

**User Journey:**
```
User selects runner type → Configures judge criteria → 
Sets scoring parameters → Saves as reusable config
```

### 3. 🚀 Run Management (`/evaluations/runs`)

**Features:**
- **Create New Run**
  - Select task set + config
  - Run preview/estimation
  - Batch size selection
  - Schedule/trigger run
- **Active Runs**
  - Real-time progress tracking
  - Live status updates
  - Cancel/pause controls
  - Resource usage monitoring
- **Run History**
  - Filter by date/status/config
  - Compare multiple runs
  - Export results

**User Journey:**
```
User combines task set + config → Reviews run parameters → 
Starts evaluation → Monitors progress → Views completion
```

### 4. 📊 Results & Analytics (`/evaluations/results`)

**Features:**
- **Individual Run Results**
  - Task-by-task breakdown
  - Score visualizations
  - Error analysis
  - Raw response viewer
- **Comparative Analysis**
  - Runner performance comparison
  - Radar charts by dimension
  - Statistical summaries
  - A/B test results
- **Export & Reporting**
  - CSV/JSON export
  - PDF reports
  - Dashboard sharing

**User Journey:**
```
User views run results → Analyzes scores by dimension → 
Compares with other runs → Exports findings → Shares insights
```

## 🔗 Required API Endpoints

### Task Management API
```typescript
// /api/evaluations/tasks
GET    /api/evaluations/tasks?user_id={id}                    // List task sets
POST   /api/evaluations/tasks                                 // Create task set  
GET    /api/evaluations/tasks/{task_set_id}                   // Get task set
PUT    /api/evaluations/tasks/{task_set_id}                   // Update task set
DELETE /api/evaluations/tasks/{task_set_id}                   // Delete task set
POST   /api/evaluations/tasks/{task_set_id}/upload            // Upload tasks (CSV/JSON)
GET    /api/evaluations/tasks/{task_set_id}/export            // Export task set
```

### Configuration API
```typescript
// /api/evaluations/configs  
GET    /api/evaluations/configs?user_id={id}                  // List eval configs
POST   /api/evaluations/configs                               // Create config
GET    /api/evaluations/configs/{config_id}                   // Get config
PUT    /api/evaluations/configs/{config_id}                   // Update config
DELETE /api/evaluations/configs/{config_id}                   // Delete config
GET    /api/evaluations/configs/templates                     // Get templates
```

### Runs API
```typescript
// /api/evaluations/runs
GET    /api/evaluations/runs?user_id={id}                     // List runs
POST   /api/evaluations/runs                                  // Create run
GET    /api/evaluations/runs/{run_id}                         // Get run details
PUT    /api/evaluations/runs/{run_id}/cancel                  // Cancel run
GET    /api/evaluations/runs/{run_id}/status                  // Get run status
GET    /api/evaluations/runs/{run_id}/results                 // Get run results
GET    /api/evaluations/runs/{run_id}/progress                // Get progress (SSE)
POST   /api/evaluations/runs/compare                          // Compare runs
```

### Results API
```typescript
// /api/evaluations/results
GET    /api/evaluations/results/{run_id}                      // Get detailed results
GET    /api/evaluations/results/{run_id}/export               // Export results
POST   /api/evaluations/results/analyze                       // Batch analysis
GET    /api/evaluations/results/dashboard/{dashboard_id}      // Shared dashboard
```

## 📱 UI Views & Components Design

### Main Evaluation Page: `/evaluations`

```tsx
// Similar to WorkflowManager pattern
export const EvaluationManager: React.FC = () => {
  // State management
  const [currentView, setCurrentView] = useState<'tasks' | 'configs' | 'runs' | 'results'>('runs');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  return (
    <div className="flex h-screen">
      <EvaluationSidebar 
        isOpen={isSidebarOpen}
        onToggle={setIsSidebarOpen}
        currentView={currentView}
        onViewChange={setCurrentView}
      />
      <main className="flex-1">
        {currentView === 'tasks' && <TaskManager />}
        {currentView === 'configs' && <ConfigManager />}
        {currentView === 'runs' && <RunManager />}
        {currentView === 'results' && <ResultsManager />}
      </main>
    </div>
  );
};
```

### 1. Task Manager Component

**Layout**: Split view with task set list (1/3) + detail view (2/3)

**Features**:
- Task set creation modal
- CSV/JSON upload modal
- Task preview cards
- Inline editing
- Tag management

```tsx
const TaskManager = () => {
  const [taskSets, setTaskSets] = useState<TaskSet[]>([]);
  const [selectedTaskSet, setSelectedTaskSet] = useState<TaskSet | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  
  return (
    <div className="flex">
      {/* Task Set List */}
      <div className="w-1/3 border-r">
        <div className="p-4 border-b">
          <Button.Group>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus /> New Task Set
            </Button>
            <Button onClick={() => setShowUploadModal(true)}>
              <Upload /> Upload Tasks
            </Button>
          </Button.Group>
        </div>
        
        <TaskSetList 
          taskSets={taskSets}
          selectedId={selectedTaskSet?.id}
          onSelect={setSelectedTaskSet}
        />
      </div>
      
      {/* Task Set Detail */}
      <div className="flex-1">
        {selectedTaskSet ? (
          <TaskSetDetail 
            taskSet={selectedTaskSet}
            onUpdate={handleUpdateTaskSet}
          />
        ) : (
          <EmptyState message="Select a task set to view details" />
        )}
      </div>
    </div>
  );
};
```

### 2. Configuration Manager

**Layout**: Split view with config list (1/3) + visual builder (2/3)

**Features**:
- Visual configuration builder
- Runner/judge selection dropdowns
- Criteria editor with custom prompts
- Template library
- Preview/test functionality

```tsx
const ConfigManager = () => {
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<EvalConfig | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);
  
  return (
    <div className="flex">
      {/* Config List */}
      <div className="w-1/3 border-r">
        <div className="p-4 border-b">
          <Button onClick={() => setShowBuilder(true)}>
            <Settings /> New Configuration
          </Button>
        </div>
        
        <ConfigList 
          configs={configs}
          selectedId={selectedConfig?.id}
          onSelect={setSelectedConfig}
        />
      </div>
      
      {/* Config Builder */}
      <div className="flex-1">
        {showBuilder || selectedConfig ? (
          <ConfigBuilder 
            config={selectedConfig}
            onSave={handleSaveConfig}
            onCancel={() => setShowBuilder(false)}
          />
        ) : (
          <EmptyState message="Select or create a configuration" />
        )}
      </div>
    </div>
  );
};
```

### 3. Run Manager

**Layout**: Split view with run list (1/3) + run detail/monitoring (2/3)

**Features**:
- Run creation wizard
- Real-time progress tracking
- Status indicators
- Cancel/pause controls
- Resource monitoring

```tsx
const RunManager = () => {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<EvalRun | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  return (
    <div className="flex">
      {/* Run List */}
      <div className="w-1/3 border-r">
        <div className="p-4 border-b">
          <Button type="primary" onClick={() => setShowCreateModal(true)}>
            <Play /> Start Evaluation
          </Button>
        </div>
        
        <RunList 
          runs={runs}
          selectedId={selectedRun?.id}
          onSelect={setSelectedRun}
        />
      </div>
      
      {/* Run Detail */}
      <div className="flex-1">
        {selectedRun ? (
          <RunDetail 
            run={selectedRun}
            onCancel={handleCancelRun}
          />
        ) : (
          <EmptyState message="Select a run to view details" />
        )}
      </div>
    </div>
  );
};
```

### 4. Results Manager

**Layout**: Full-width with toolbar + switchable view modes

**Features**:
- Table/charts/comparison view modes
- Interactive visualizations
- Export functionality
- Filtering and search
- Comparative analysis tools

```tsx
const ResultsManager = () => {
  const [results, setResults] = useState<EvalResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<EvalResult | null>(null);
  const [viewMode, setViewMode] = useState<'table' | 'charts' | 'compare'>('table');
  
  return (
    <div className="flex flex-col">
      {/* Toolbar */}
      <div className="p-4 border-b">
        <div className="flex justify-between">
          <Radio.Group value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
            <Radio.Button value="table">
              <Table /> Table View
            </Radio.Button>
            <Radio.Button value="charts">
              <BarChart /> Charts
            </Radio.Button>
            <Radio.Button value="compare">
              <GitCompare /> Compare
            </Radio.Button>
          </Radio.Group>
          
          <Button.Group>
            <Button><Download /> Export</Button>
            <Button><Share /> Share</Button>
          </Button.Group>
        </div>
      </div>
      
      {/* Results Content */}
      <div className="flex-1">
        {viewMode === 'table' && <ResultsTable results={results} />}
        {viewMode === 'charts' && <ResultsCharts results={results} />}
        {viewMode === 'compare' && <ResultsComparison results={results} />}
      </div>
    </div>
  );
};
```

## 🧩 Key Reusable Components

### Status Components
```tsx
// Status indicator with real-time updates
const RunStatus = ({ status, progress }: { status: EvalRunStatus, progress?: number }) => (
  <div className="flex items-center gap-2">
    <StatusIcon status={status} />
    <span>{status}</span>
    {progress && <Progress percent={progress} size="small" />}
  </div>
);
```

### Data Visualization
```tsx
// Interactive task preview
const TaskPreview = ({ task }: { task: EvalTask }) => (
  <Card size="small">
    <div className="space-y-2">
      <Text strong>{task.name}</Text>
      <Paragraph ellipsis={{ rows: 2 }}>{task.description}</Paragraph>
      <Tag color="blue">{task.input.length} inputs</Tag>
    </div>
  </Card>
);

// Score visualization radar chart
const ScoreRadar = ({ scores }: { scores: EvalScore[] }) => (
  <ResponsiveRadar
    data={transformScoresForRadar(scores)}
    keys={['score']}
    indexBy="dimension"
    maxValue={10}
  />
);
```

### Form Components
```tsx
// Configuration builder forms
const RunnerConfigForm = ({ config, onChange }) => { /* ... */ };
const JudgeConfigForm = ({ config, onChange }) => { /* ... */ };
const CriteriaEditor = ({ criteria, onChange }) => { /* ... */ };
```

## 🚀 Implementation Roadmap

### Phase 1: MVP (Core Functionality)
**Timeline**: 2-3 weeks

**Backend:**
- Basic evaluation API endpoints (`/tasks`, `/configs`, `/runs`)
- Integration with existing orchestrator
- Database schema for eval entities

**Frontend:**
- Main evaluation page with 4-tab navigation
- Basic task management (create, list, view)
- Simple run creation and status tracking
- Results table view

**Success Criteria:**
- Users can create task sets manually
- Users can configure basic model/team runners
- Users can start evaluations and see results
- Results display in tabular format

### Phase 2: Enhanced Experience (Polish & Features)
**Timeline**: 3-4 weeks

**Backend:**
- Task upload/import functionality
- Real-time progress via Server-Sent Events
- Advanced filtering and search
- Export endpoints

**Frontend:**
- Configuration builder with visual UI
- Real-time progress updates with WebSocket/SSE
- Charts and visualization components
- Task templates and CSV/JSON upload
- Advanced filtering and search

**Success Criteria:**
- Users can upload task sets via CSV/JSON
- Live progress tracking during runs
- Visual score comparisons with charts
- Template library for common eval patterns

### Phase 3: Advanced Analytics (Production Ready)
**Timeline**: 4-5 weeks

**Backend:**
- Comparative analysis endpoints
- Dashboard sharing functionality
- Advanced statistics and reporting
- Integration with teams/workflows

**Frontend:**
- Advanced analytics and reporting
- Dashboard sharing and collaboration
- A/B testing workflows
- Integration with existing teams/workflows
- Performance optimizations

**Success Criteria:**
- Comprehensive evaluation analytics
- Team collaboration features
- Production-ready performance
- Full integration with AutoGen Studio ecosystem

## 📊 Success Metrics

### User Engagement
- **Task Set Creation**: Users create and reuse task sets
- **Run Frequency**: Regular evaluation runs per user
- **Result Analysis**: Time spent analyzing results

### Performance
- **Batch Processing**: 10x faster evaluation runs
- **UI Responsiveness**: <200ms page load times
- **Real-time Updates**: Live progress tracking

### Adoption
- **Feature Usage**: All 4 main views actively used
- **Template Reuse**: Common evaluation patterns shared
- **Export Utilization**: Results exported for external analysis

## 🎯 Conclusion

This comprehensive evaluation system design provides AutoGen Studio users with a complete workflow for LLM/agent evaluation, from task creation through results analysis. By leveraging existing UI patterns and the new batch-native backend architecture, we can deliver a powerful, scalable, and user-friendly evaluation experience that scales from simple experiments to production evaluation workflows.

The phased implementation approach ensures rapid delivery of core value while building toward advanced analytics and collaboration features that will position AutoGen Studio as a leading platform for AI evaluation and analysis.