# Data Collection Tools

Tools to fetch GitHub issues while managing API rate limits.

## 📋 Option 1: Manually Specify Issues (Recommended for Rate Limits)

Create a text file with issue URLs or numbers you want to analyze.

### Create issues.txt

```txt
# Add issue URLs or numbers (one per line)
https://github.com/ROCm/TheRock/issues/2112
https://github.com/ROCm/TheRock/issues/2111
2110
2109
2108
```

### Fetch Those Issues

```bash
cd /Users/sahilfaizal/Downloads/TheRock-main/dashboards/data-collection
source ../../venv/bin/activate

# Fetch and save to JSON
python load_from_file.py issues.txt -o my_issues.json
```

**Benefits:**
- ✅ Only fetches issues you care about (minimal API usage)
- ✅ Works even when rate limited
- ✅ Fast and efficient
- ✅ Can curate specific issues for testing

## 📦 Option 2: Export All Issues

Export all open and closed issues to work offline.

```bash
cd /Users/sahilfaizal/Downloads/TheRock-main/dashboards/data-collection
source ../../venv/bin/activate

# Export 100 open + 200 closed issues
python export_issues.py

# Custom limits
python export_issues.py --open-limit 50 --closed-limit 100

# Custom output file
python export_issues.py -o backup_issues.json
```

**Output:** `issues_export.json`

**Benefits:**
- ✅ One-time API usage
- ✅ Complete dataset for analysis
- ✅ Can work completely offline after export

## 🔄 Use Exported Data in Dashboard

After exporting, configure the backend to use the JSON file:

Edit `dashboards/backend/.env`:
```env
OFFLINE_ISSUES_FILE=../data-collection/issues_export.json
```

Restart the backend, and it will use the local file instead of GitHub API! (Note: This feature requires backend modification - coming soon)

## 📊 Checking Your Rate Limit

See how many API calls you have left:

```bash
cd /Users/sahilfaizal/Downloads/TheRock-main/dashboards/backend
source ../../venv/bin/activate

python << 'EOF'
from github import Github
import os
from dotenv import load_dotenv

load_dotenv()
g = Github(os.getenv('GITHUB_TOKEN'))
rate = g.get_rate_limit()

print("=" * 60)
print("GitHub API Rate Limit Status")
print("=" * 60)
print(f"Core API:")
print(f"  Remaining: {rate.core.remaining}/{rate.core.limit}")
print(f"  Resets at: {rate.core.reset}")
print(f"  Time until reset: {(rate.core.reset - __import__('datetime').datetime.now()).total_seconds() / 60:.1f} minutes")
print()
print(f"Search API:")
print(f"  Remaining: {rate.search.remaining}/{rate.search.limit}")
print("=" * 60)
EOF
```

## 💡 Recommended Workflow

### For Development/Testing:
1. Create `issues.txt` with 5-10 interesting issues
2. Run `python load_from_file.py issues.txt -o test_issues.json`
3. Use dashboard normally (caching prevents repeated API calls)

### For Production/Analysis:
1. Export all issues once: `python export_issues.py`
2. Use cached data (expires after 1-24 hours)
3. Re-export weekly to get new issues

### When Rate Limited:
1. Wait for reset (check with script above)
2. Use previously exported JSON files
3. Work with manual issue list (Option 1)

## 📝 File Formats

### issues.txt Format
```txt
# Lines starting with # are comments

# Full URLs work:
https://github.com/ROCm/TheRock/issues/123

# Just numbers work too:
456
789

# Mix and match:
https://github.com/ROCm/TheRock/issues/101
102
```

### Output JSON Format
```json
{
  "source_file": "issues.txt",
  "repository": "ROCm/TheRock",
  "issues": [
    {
      "number": 123,
      "title": "Issue title",
      "body": "Issue description...",
      "state": "open",
      "labels": [...],
      ...
    }
  ],
  "total_fetched": 10,
  "failed_issues": []
}
```

## 🚀 Quick Start Examples

### Example 1: Analyze 10 Specific Issues
```bash
# 1. Create issues list
cat > my_issues.txt << 'EOF'
2112
2111
2110
2109
2108
2107
2106
2105
2104
2103
EOF

# 2. Fetch them
python load_from_file.py my_issues.txt -o analysis_set.json

# 3. Only uses 10 API calls!
```

### Example 2: Work Completely Offline
```bash
# 1. Export once (uses ~50-100 API calls)
python export_issues.py --open-limit 100 --closed-limit 200

# 2. Work offline for days/weeks
# Backend uses cache automatically

# 3. Re-export when you need fresh data
```

### Example 3: Find Interesting Issues on GitHub First
```bash
# 1. Browse GitHub: https://github.com/ROCm/TheRock/issues
# 2. Copy URLs of interesting issues
# 3. Paste into issues.txt
# 4. Fetch with load_from_file.py
# 5. Analyze with dashboard!
```

## 🎯 API Usage Comparison

| Method | API Calls | Best For |
|--------|-----------|----------|
| Manual list (10 issues) | 10 | Targeted analysis, rate limited |
| Export all (100 open + 200 closed) | ~50-100 | One-time setup, complete data |
| Dashboard with cache | 0* | Daily use (*after first fetch) |
| No cache | 5-10 per page load | Testing only |

## 🔐 Rate Limits

- **No token**: 60 requests/hour
- **With token**: 5,000 requests/hour
- **Resets**: Every hour (on the hour)

## 🛠️ Troubleshooting

### "Rate limit exceeded"
- Check remaining calls (see script above)
- Wait for reset
- Use exported/manual files instead

### "Issue not found"
- Check issue number is correct
- Verify repository in .env
- Issue might be from a different repo

### "No token"
- Set GITHUB_TOKEN in .env
- Regenerate token if expired
- Check token has `repo` scope

## 📚 More Resources

- [GitHub API Rate Limiting](https://docs.github.com/en/rest/rate-limit)
- [Creating GitHub Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Backend Caching Documentation](../README.md#caching)
