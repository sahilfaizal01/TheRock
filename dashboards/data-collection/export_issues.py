#!/usr/bin/env python3
"""
Export issues from GitHub to a local JSON file.
This allows you to work offline and avoid rate limits.
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
from services.github_service import GitHubService

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))


def export_issues(output_file: str = "issues_export.json", open_limit: int = 100, closed_limit: int = 200):
    """Export issues to a JSON file"""

    print("=" * 60)
    print("GitHub Issues Exporter")
    print("=" * 60)
    print()

    # Initialize GitHub service
    repo_owner = os.getenv("GITHUB_REPO_OWNER", "ROCm")
    repo_name = os.getenv("GITHUB_REPO_NAME", "TheRock")

    print(f"Repository: {repo_owner}/{repo_name}")
    print(f"Open issues limit: {open_limit}")
    print(f"Closed issues limit: {closed_limit}")
    print()

    gh_service = GitHubService(repo_owner=repo_owner, repo_name=repo_name, use_cache=False)

    # Fetch open issues
    print("Fetching open issues...")
    try:
        open_issues = gh_service.get_open_issues(limit=open_limit, force_refresh=True)
        print(f"✓ Fetched {len(open_issues)} open issues")
    except Exception as e:
        print(f"✗ Error fetching open issues: {e}")
        open_issues = []

    # Fetch closed issues
    print("Fetching closed issues...")
    try:
        closed_issues = gh_service.get_closed_issues(days=180, limit=closed_limit, force_refresh=True)
        print(f"✓ Fetched {len(closed_issues)} closed issues")
    except Exception as e:
        print(f"✗ Error fetching closed issues: {e}")
        closed_issues = []

    # Prepare export data
    export_data = {
        'exported_at': datetime.now().isoformat(),
        'repository': f"{repo_owner}/{repo_name}",
        'open_issues': open_issues,
        'closed_issues': closed_issues,
        'stats': {
            'total_open': len(open_issues),
            'total_closed': len(closed_issues)
        }
    }

    # Write to file
    print()
    print(f"Writing to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)

    file_size = os.path.getsize(output_file) / 1024 / 1024  # MB
    print(f"✓ Export complete! ({file_size:.2f} MB)")
    print()
    print("=" * 60)
    print(f"Exported {len(open_issues)} open issues and {len(closed_issues)} closed issues")
    print(f"File: {os.path.abspath(output_file)}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export GitHub issues to JSON file")
    parser.add_argument('-o', '--output', default='issues_export.json', help='Output JSON file')
    parser.add_argument('--open-limit', type=int, default=100, help='Number of open issues to fetch')
    parser.add_argument('--closed-limit', type=int, default=200, help='Number of closed issues to fetch')

    args = parser.parse_args()

    export_issues(args.output, args.open_limit, args.closed_limit)
