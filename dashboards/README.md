# TheRock Issue Analysis Dashboard

AI-powered dashboard for analyzing GitHub issues in the ROCm/TheRock repository. This system automatically:
- Fetches open issues from the repository
- Analyzes them using Claude AI
- Categorizes issues by responsible ROCm component
- Finds similar historical issues that were resolved
- Traces back to potential root cause commits/PRs
- Generates fix suggestions

## Features

### 🤖 AI-Powered Analysis
- Uses Claude 3.5 Sonnet for intelligent issue analysis
- Categorizes issues by ROCm components (compiler, runtime, math-libs, ml-libs, etc.)
- Determines severity levels (critical, high, medium, low)
- Generates actionable fix suggestions

### 🔍 Similar Issue Detection
- Uses TF-IDF vectorization and cosine similarity
- Finds historical issues that were successfully resolved
- Provides resolution summaries from closed issues

### 🔬 Root Cause Tracing
- Analyzes git commit history
- Identifies commits that likely introduced the issue
- Traces commits affecting specific component paths
- Links to the responsible PR/commit

### 🏷️ Automatic Labeling
- Suggests component-specific labels
- Severity-based labels
- Can automatically apply labels to issues (with proper permissions)

## Architecture

```
dashboards/
├── backend/                    # FastAPI backend
│   ├── app.py                 # Main API application
│   ├── models/                # Pydantic data models
│   │   └── issue.py
│   ├── services/              # Business logic
│   │   ├── github_service.py  # GitHub API integration
│   │   ├── ai_analyzer.py     # Claude AI analysis
│   │   └── git_tracer.py      # Git history analysis
│   └── requirements.txt       # Python dependencies
├── frontend/                   # Web UI
│   └── index.html             # Single-page dashboard
└── docs/                       # Documentation
```

## Setup Instructions

### Prerequisites

1. **Python 3.9+**
2. **GitHub Personal Access Token** with `repo` scope
3. **Anthropic API Key** for Claude access

### Installation

1. **Navigate to the dashboard backend:**
   ```bash
   cd dashboards/backend
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:
   ```env
   GITHUB_TOKEN=your_github_token_here
   GITHUB_REPO_OWNER=ROCm
   GITHUB_REPO_NAME=TheRock
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   PORT=8000
   DEBUG=True
   ```

### Running the Dashboard

1. **Start the backend API:**
   ```bash
   cd dashboards/backend
   python app.py
   ```

   The API will be available at `http://localhost:8000`

2. **Open the frontend:**
   ```bash
   cd dashboards/frontend
   # Serve with any static file server, e.g.:
   python -m http.server 3000
   ```

   Open `http://localhost:3000` in your browser

## API Endpoints

### Health Check
```
GET /api/health
```
Returns the health status of the service and configured integrations.

### Get Issues
```
GET /api/issues?limit=20&state=open
```
Fetch issues from the repository.

**Parameters:**
- `limit` (int): Number of issues to fetch (default: 20)
- `state` (string): "open" or "closed"

### Analyze Issues
```
POST /api/analyze
```
Analyze issues using AI and provide comprehensive insights.

**Request Body:**
```json
{
  "analyze_all_open": true,
  "limit": 10
}
```

**Response:**
```json
{
  "analyses": [
    {
      "issue_number": 123,
      "title": "Build failure on gfx1100",
      "component_categories": [
        {
          "component": "compiler",
          "confidence": 0.85,
          "reasoning": "Matched keywords: llvm, hip, compilation"
        }
      ],
      "similar_issues": [
        {
          "number": 100,
          "title": "Similar compilation error",
          "similarity_score": 0.78
        }
      ],
      "root_cause_commits": [
        {
          "sha": "abc123",
          "message": "Update LLVM version",
          "confidence_score": 0.7
        }
      ],
      "fix_suggestions": [
        "Check LLVM compatibility",
        "Review recent compiler changes"
      ],
      "severity": "high"
    }
  ],
  "total_analyzed": 1,
  "timestamp": "2025-12-14T..."
}
```

### Add Labels to Issue
```
POST /api/issues/{issue_number}/add-labels
```
Add suggested labels to an issue (requires write permissions).

### Get Statistics
```
GET /api/stats
```
Returns dashboard statistics (open issues, closed issues, etc.)

## ROCm Component Categories

The system automatically categorizes issues into these ROCm components:

- **compiler**: LLVM, HIP, HIPIFY, compilation issues
- **runtime**: HIP runtime, device management, memory
- **math-libs**: rocBLAS, rocSOLVER, rocFFT, rocRAND
- **ml-libs**: MIOpen, composable kernel, ML frameworks
- **comm-libs**: RCCL, communication libraries
- **profiler**: rocprof, profiling tools
- **pytorch**: PyTorch integration
- **build-system**: CMake, build configuration
- **packaging**: RPM, DEB, installation
- **ci-cd**: GitHub Actions, workflows
- **gpu-arch**: GPU architecture specific (gfx94X, gfx110X, etc.)
- **core**: ROCm core, AMDSMI
- **base**: Half precision, rocm-cmake

## Usage Examples

### Example 1: Analyze All Open Issues

```python
import requests

response = requests.post('http://localhost:8000/api/analyze', json={
    'analyze_all_open': True,
    'limit': 10
})

data = response.json()
for analysis in data['analyses']:
    print(f"Issue #{analysis['issue_number']}: {analysis['title']}")
    print(f"Severity: {analysis['severity']}")
    print(f"Components: {[c['component'] for c in analysis['component_categories']]}")
    print(f"Fix Suggestions: {analysis['fix_suggestions']}")
    print("---")
```

### Example 2: Analyze Specific Issues

```python
response = requests.post('http://localhost:8000/api/analyze', json={
    'issue_numbers': [123, 124, 125]
})
```

### Example 3: Get Git Blame for a File

```python
response = requests.get('http://localhost:8000/api/git/blame/compiler/llvm/CMakeLists.txt')
blame_data = response.json()
```

## How It Works

### 1. Issue Fetching
The GitHub service uses PyGithub to fetch issues from the repository, including metadata like labels, comments, creation date, etc.

### 2. Component Categorization
Issues are categorized using keyword matching against a predefined map of ROCm components. The confidence score indicates how strongly the issue relates to each component.

### 3. Similar Issue Finding
- Extracts text from issue title and body
- Computes TF-IDF vectors for all issues
- Calculates cosine similarity between current and historical issues
- Returns top K most similar issues

### 4. Root Cause Tracing
- Analyzes git commit history since issue creation
- Identifies commits affecting relevant component paths
- Scores commits based on file changes and timing
- Returns commits with confidence scores

### 5. AI Analysis (Claude)
- Sends issue context to Claude 3.5 Sonnet
- Requests severity assessment, summary, and fix suggestions
- Parses structured JSON response
- Falls back gracefully if AI is unavailable

## Development

### Adding New ROCm Components

Edit `backend/services/ai_analyzer.py` and update the `ROCM_COMPONENTS` dictionary:

```python
ROCM_COMPONENTS = {
    "new-component": ["keyword1", "keyword2", "keyword3"],
    # ...
}
```

### Customizing Analysis

Modify the Claude prompt in `backend/services/ai_analyzer.py` → `_get_claude_analysis()` method.

### Extending the API

Add new endpoints to `backend/app.py` following the FastAPI pattern.

## Troubleshooting

### "GitHub API rate limit exceeded"
- Use an authenticated GitHub token with higher rate limits
- Reduce the number of issues analyzed per request

### "Anthropic API error"
- Verify your API key is correct
- Check your API usage quota
- Ensure you have access to Claude 3.5 Sonnet

### "Git repository not found"
- Ensure the backend is running from within the TheRock repository
- Check that the repository path in `git_tracer.py` is correct

### CORS errors in frontend
- Ensure the backend API is running
- Check that `API_BASE` in `frontend/index.html` points to the correct backend URL

## Future Enhancements

- [ ] Database integration (Redshift) for persistent storage
- [ ] Real-time issue monitoring with webhooks
- [ ] Automatic label application
- [ ] Integration with CI/CD pipeline
- [ ] Historical trend analysis and reporting
- [ ] Email notifications for critical issues
- [ ] Multi-repository support
- [ ] Advanced filtering and search
- [ ] Issue priority recommendations
- [ ] Team assignment suggestions

## License

This dashboard is part of the ROCm/TheRock project and follows the same license.

## Contributing

Contributions are welcome! Please follow the TheRock contribution guidelines.

## Support

For issues or questions about this dashboard, please open an issue in the ROCm/TheRock repository with the `component:dashboard` label.
