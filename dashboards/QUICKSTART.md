# Quick Start Guide

Get the TheRock Issue Analysis Dashboard running in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- GitHub Personal Access Token ([Create one here](https://github.com/settings/tokens))
- Anthropic API Key ([Get one here](https://console.anthropic.com/))

## Step 1: Get API Keys

### GitHub Token
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name like "TheRock Dashboard"
4. Select scopes: `repo` (full control)
5. Click "Generate token"
6. Copy the token (you won't see it again!)

### Anthropic API Key
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key

## Step 2: Configure Environment

```bash
cd dashboards/backend
cp .env.example .env
```

Edit `.env` and paste your keys:
```env
GITHUB_TOKEN=ghp_your_token_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
GITHUB_REPO_OWNER=ROCm
GITHUB_REPO_NAME=TheRock
PORT=8000
```

## Step 3: Install Dependencies

```bash
cd dashboards/backend
pip install -r requirements.txt
```

Or use a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 4: Run the Dashboard

### Easy Way (Automated)
```bash
cd dashboards
./start.sh
```

### Manual Way

**Terminal 1 - Backend:**
```bash
cd dashboards/backend
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd dashboards/frontend
python -m http.server 3000
```

## Step 5: Use the Dashboard

1. Open your browser to **http://localhost:3000**
2. Click **"Load Open Issues"** to see current issues
3. Click **"Analyze All Issues"** to run AI analysis (this takes 30-60 seconds)
4. Explore the results!

## What You'll See

### Issue Analysis Results
Each analyzed issue shows:
- **Severity**: Critical, High, Medium, or Low
- **ROCm Components**: Which parts of ROCm are affected
- **Similar Issues**: Historical issues that were resolved
- **Root Cause Commits**: Potential commits that introduced the bug
- **Fix Suggestions**: AI-generated recommendations

### Example Output

```
Issue #123: Build failure on gfx1100

Severity: HIGH

Analysis: The issue appears to be related to LLVM compilation changes
that affect gfx1100 architecture. Recent updates to the compiler may
have introduced incompatibilities.

ROCm Components:
- compiler (85%)
- gpu-arch (70%)

Similar Historical Issues:
- #100: LLVM build error on MI200 (78% similar) [CLOSED]
- #87: Compilation regression after LLVM update (65% similar) [CLOSED]

Potential Root Cause Commits:
- abc1234: Update LLVM to version 18 (70% confidence)
- def5678: Add gfx1100 support (50% confidence)

Fix Suggestions:
1. Review LLVM version compatibility with gfx1100
2. Check for architecture-specific compilation flags
3. Verify device code generation for RDNA3
```

## Common Issues

### "GitHub API rate limit exceeded"
**Solution**: Make sure you're using a GitHub token (not running anonymously)

### "Anthropic API error: Invalid API key"
**Solution**: Double-check your API key in `.env` file

### "Module not found" errors
**Solution**: Install dependencies: `pip install -r requirements.txt`

### Frontend can't connect to backend
**Solution**: Make sure backend is running on port 8000, check console for errors

### CORS errors
**Solution**: Access frontend via http://localhost:3000, not file:///

## API Examples

### Get Issues via API
```bash
curl http://localhost:8000/api/issues?limit=5
```

### Analyze Issues via API
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"analyze_all_open": true, "limit": 3}'
```

### Check Health
```bash
curl http://localhost:8000/api/health
```

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand the system
- Customize component categories in `backend/services/ai_analyzer.py`
- Integrate with CI/CD workflows

## Tips

1. **Start Small**: Analyze 3-5 issues first to test everything works
2. **Rate Limits**: Be mindful of GitHub and Anthropic API limits
3. **Caching**: The system fetches closed issues once - restart to refresh
4. **Costs**: Each analysis uses ~1K tokens of Claude API (~$0.003 per issue)

## Getting Help

- Check the logs in the terminal for error messages
- Visit the [GitHub repository](https://github.com/ROCm/TheRock)
- Open an issue with label `component:dashboard`

Happy analyzing! 🚀
