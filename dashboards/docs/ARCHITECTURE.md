# Dashboard Architecture

## System Overview

The TheRock Issue Analysis Dashboard is a full-stack application consisting of:
- **Backend**: FastAPI-based REST API (Python)
- **Frontend**: Single-page HTML/JavaScript application
- **AI Engine**: Claude 3.5 Sonnet for intelligent analysis
- **Data Sources**: GitHub API, Git repository, (optional) Redshift

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Browser)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   index.html (Vanilla JS)                                 │  │
│  │   - Issue list display                                    │  │
│  │   - Analysis visualization                                │  │
│  │   - Statistics dashboard                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   app.py - REST API Endpoints                            │  │
│  │   /api/issues - Fetch issues                             │  │
│  │   /api/analyze - Analyze issues                          │  │
│  │   /api/stats - Get statistics                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────┬──────┴──────┬────────────────────────┐  │
│  │                   │             │                         │  │
│  ▼                   ▼             ▼                         ▼  │
│  ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │  GitHub     │ │   AI     │ │   Git    │ │  Data        │  │
│  │  Service    │ │ Analyzer │ │  Tracer  │ │  Models      │  │
│  └─────────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        │                 │              │
        ▼                 ▼              ▼
┌──────────────┐  ┌─────────────┐  ┌──────────┐
│  GitHub API  │  │ Claude API  │  │ Git Repo │
│   (PyGithub) │  │  (Anthropic)│  │(GitPython)│
└──────────────┘  └─────────────┘  └──────────┘
```

## Component Details

### 1. Frontend Layer

**Technology**: Vanilla HTML/CSS/JavaScript
**File**: `frontend/index.html`

**Responsibilities**:
- Render issue list and analysis results
- Provide user controls (load issues, analyze, filter)
- Display statistics and visualizations
- Make API calls to backend

**Key Features**:
- Responsive grid layout
- Color-coded severity indicators
- Expandable issue details
- Link to GitHub for full context

### 2. Backend API Layer

**Technology**: FastAPI (Python 3.9+)
**File**: `backend/app.py`

**Responsibilities**:
- Expose REST API endpoints
- Coordinate between services
- Handle authentication/authorization
- Rate limiting and error handling

**Key Endpoints**:
- `GET /api/health` - Health check
- `GET /api/issues` - Fetch issues
- `POST /api/analyze` - Analyze issues
- `POST /api/issues/{id}/add-labels` - Add labels
- `GET /api/stats` - Get statistics

### 3. Service Layer

#### GitHub Service
**File**: `backend/services/github_service.py`
**Technology**: PyGithub

**Responsibilities**:
- Fetch open/closed issues
- Get issue details and comments
- Retrieve commit history
- Find PRs associated with commits
- Create and apply labels

**Key Methods**:
- `get_open_issues()` - Fetch open issues
- `get_closed_issues()` - Fetch closed issues
- `get_commits_since()` - Get recent commits
- `get_pull_request_for_commit()` - Find PR for a commit
- `add_label_to_issue()` - Add label to issue

#### AI Analyzer
**File**: `backend/services/ai_analyzer.py`
**Technology**: Anthropic Claude API, scikit-learn

**Responsibilities**:
- Categorize issues by ROCm component
- Find similar historical issues
- Generate fix suggestions
- Assess severity
- Identify root cause commits

**Key Methods**:
- `analyze_issue()` - Main analysis orchestrator
- `_categorize_components()` - Component categorization
- `_find_similar_issues()` - TF-IDF similarity matching
- `_get_claude_analysis()` - Claude AI insights
- `_identify_root_cause_commits()` - Root cause detection

**Component Categories**:
```python
ROCM_COMPONENTS = {
    "compiler": [...],
    "runtime": [...],
    "math-libs": [...],
    "ml-libs": [...],
    "comm-libs": [...],
    "profiler": [...],
    "pytorch": [...],
    "build-system": [...],
    "packaging": [...],
    "ci-cd": [...],
    "gpu-arch": [...],
    "core": [...],
    "base": [...]
}
```

#### Git Tracer
**File**: `backend/services/git_tracer.py`
**Technology**: GitPython

**Responsibilities**:
- Analyze git commit history
- Find commits affecting specific paths
- Git blame for files
- Identify breaking commits
- Extract file paths from errors

**Key Methods**:
- `find_commits_affecting_paths()` - Find commits for paths
- `find_commits_by_keyword()` - Search commits by keyword
- `blame_file()` - Git blame for a file
- `find_breaking_commits()` - Identify potential causes
- `get_commit_diff()` - Get diff for a commit

### 4. Data Models

**File**: `backend/models/issue.py`
**Technology**: Pydantic

**Models**:
- `IssueLabel` - GitHub label representation
- `SimilarIssue` - Similar historical issue
- `RootCauseCommit` - Potential root cause commit
- `ComponentCategory` - ROCm component classification
- `IssueAnalysis` - Complete analysis result
- `AnalysisRequest` - API request model
- `AnalysisResponse` - API response model

## Data Flow

### Issue Analysis Flow

```
1. User clicks "Analyze All Issues"
   │
   ▼
2. Frontend sends POST /api/analyze
   │
   ▼
3. Backend fetches open issues (GitHub Service)
   │
   ▼
4. Backend fetches closed issues for comparison
   │
   ▼
5. Backend fetches recent commits (Git Tracer)
   │
   ▼
6. For each issue:
   │
   ├─▶ Categorize by component (keyword matching)
   │
   ├─▶ Find similar issues (TF-IDF + cosine similarity)
   │
   ├─▶ Get AI insights (Claude API)
   │    - Severity assessment
   │    - Summary generation
   │    - Fix suggestions
   │
   ├─▶ Identify root cause commits (Git analysis)
   │
   └─▶ Generate suggested labels
   │
   ▼
7. Return aggregated analysis to frontend
   │
   ▼
8. Frontend renders analysis with visualizations
```

### Component Categorization Algorithm

```python
def categorize_components(issue):
    text = issue.title + " " + issue.body
    categories = []

    for component, keywords in ROCM_COMPONENTS.items():
        matches = count_keyword_matches(text, keywords)
        if matches > 0:
            confidence = min(matches / len(keywords) * 2, 1.0)
            categories.append({
                'component': component,
                'confidence': confidence
            })

    return sort_by_confidence(categories)[:3]
```

### Similar Issue Detection Algorithm

```python
def find_similar_issues(current_issue, historical_issues):
    # 1. Extract text
    current_text = current_issue.title + " " + current_issue.body
    historical_texts = [i.title + " " + i.body for i in historical_issues]

    # 2. TF-IDF vectorization
    vectorizer = TfidfVectorizer(max_features=500)
    vectors = vectorizer.fit_transform([current_text] + historical_texts)

    # 3. Compute cosine similarity
    similarities = cosine_similarity(vectors[0:1], vectors[1:])

    # 4. Return top K similar issues
    return top_k_indices(similarities, k=5)
```

### Root Cause Detection Algorithm

```python
def identify_root_cause_commits(issue, commits, components):
    suspects = []
    component_paths = map_components_to_paths(components)

    for commit in commits:
        confidence = 0.0

        # Check if commit touches relevant paths
        if any(file in component_paths for file in commit.files):
            confidence += 0.3

        # Check if commit mentions error keywords
        if has_error_keywords(commit.message):
            confidence += 0.2

        # Check timing (recent commits more likely)
        if is_recent(commit.date, issue.created_at):
            confidence += 0.1

        if confidence > 0.2:
            suspects.append((commit, confidence))

    return sort_by_confidence(suspects)[:5]
```

## Security Considerations

### Authentication
- GitHub token stored in environment variables
- Anthropic API key stored in environment variables
- Never commit credentials to repository

### Rate Limiting
- GitHub API: 5000 requests/hour (authenticated)
- Anthropic API: Varies by plan
- Implement caching to reduce API calls

### CORS
- Currently allows all origins (for development)
- In production, restrict to specific domains

### Input Validation
- All API inputs validated with Pydantic
- File path validation in Git tracer
- SQL injection prevention (when using database)

## Performance Optimization

### Caching Strategy
- Cache closed issues (update daily)
- Cache commit history (update hourly)
- Cache AI analysis results (24 hours)

### Concurrent Processing
- Use async/await for I/O operations
- Parallel issue analysis
- Background tasks for long-running operations

### Database Integration (Future)
- Store analysis results in Redshift
- Reduce repeated API calls
- Historical trend analysis

## Deployment

### Local Development
```bash
cd dashboards
./start.sh
```

### Docker Deployment
```dockerfile
# Future: Add Dockerfile for containerization
```

### Production Considerations
- Use Gunicorn/Uvicorn workers
- Add Redis for caching
- Set up monitoring (Prometheus/Grafana)
- Configure proper CORS origins
- Use environment-specific configs

## Extensibility

### Adding New Analysis Features

1. **Create new service** in `backend/services/`
2. **Update models** in `backend/models/`
3. **Add API endpoint** in `backend/app.py`
4. **Update frontend** to display results

### Integrating with CI/CD

```yaml
# .github/workflows/issue-analysis.yml
name: Analyze New Issues
on:
  issues:
    types: [opened]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run analysis
        run: |
          curl -X POST http://dashboard/api/analyze \
            -d '{"issue_numbers": [${{ github.event.issue.number }}]}'
```

## Monitoring and Observability

### Metrics to Track
- API response times
- GitHub API rate limit usage
- Anthropic API usage and costs
- Analysis accuracy (manual validation)
- Issue resolution correlation

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized log aggregation (future)

## Testing Strategy

### Unit Tests
- Service layer functions
- Component categorization logic
- Similarity detection accuracy
- Commit analysis algorithms

### Integration Tests
- GitHub API integration
- Claude API integration
- Git repository operations

### End-to-End Tests
- Full analysis workflow
- Frontend-backend communication
- Label application

## Future Architecture Improvements

1. **Microservices**: Split into separate services
2. **Message Queue**: Use RabbitMQ for async processing
3. **Database**: PostgreSQL for persistent storage
4. **Caching**: Redis for performance
5. **Authentication**: OAuth for user management
6. **Webhooks**: Real-time issue monitoring
7. **Machine Learning**: Custom models for better categorization
8. **GraphQL**: More flexible API queries
