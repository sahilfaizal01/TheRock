"""
Load issues from a text file containing GitHub issue URLs or numbers.

Example issues.txt format:
https://github.com/ROCm/TheRock/issues/123
https://github.com/ROCm/TheRock/issues/456
789
https://github.com/ROCm/TheRock/issues/101

Or just issue numbers:
123
456
789
"""

import os
import sys
import json
import re
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
from services.github_service import GitHubService

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))


def parse_issue_file(file_path: str) -> List[int]:
    """Parse issue numbers from a text file"""
    issue_numbers = []

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Try to extract issue number from URL or plain number
            # Matches: https://github.com/ROCm/TheRock/issues/123
            url_match = re.search(r'/issues/(\d+)', line)
            if url_match:
                issue_numbers.append(int(url_match.group(1)))
            elif line.isdigit():
                issue_numbers.append(int(line))

    return issue_numbers


def fetch_issues_from_file(input_file: str, output_file: str = None):
    """Fetch specific issues from GitHub based on a text file"""

    print("=" * 60)
    print("GitHub Issues Loader from File")
    print("=" * 60)
    print()

    # Parse issue numbers
    print(f"Reading issue list from: {input_file}")
    issue_numbers = parse_issue_file(input_file)
    print(f"Found {len(issue_numbers)} issues to fetch")
    print()

    if not issue_numbers:
        print("No valid issue numbers found in file!")
        return

    # Initialize GitHub service
    repo_owner = os.getenv("GITHUB_REPO_OWNER", "ROCm")
    repo_name = os.getenv("GITHUB_REPO_NAME", "TheRock")

    print(f"Repository: {repo_owner}/{repo_name}")
    print()

    gh_service = GitHubService(repo_owner=repo_owner, repo_name=repo_name, use_cache=False)

    # Fetch each issue
    issues = []
    failed = []

    for i, issue_num in enumerate(issue_numbers, 1):
        print(f"[{i}/{len(issue_numbers)}] Fetching issue #{issue_num}...", end=' ')
        try:
            issue = gh_service.get_issue_by_number(issue_num)
            issues.append(issue)
            print(f"✓ {issue['title'][:50]}...")
        except Exception as e:
            print(f"✗ Error: {e}")
            failed.append(issue_num)

    print()
    print("=" * 60)
    print(f"Successfully fetched: {len(issues)}/{len(issue_numbers)} issues")
    if failed:
        print(f"Failed: {failed}")
    print("=" * 60)
    print()

    # Save to JSON if output file specified
    if output_file:
        export_data = {
            'source_file': input_file,
            'repository': f"{repo_owner}/{repo_name}",
            'issues': issues,
            'total_fetched': len(issues),
            'failed_issues': failed
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"Saved to: {output_file}")
        print()

    return issues


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch GitHub issues from a text file")
    parser.add_argument('input', help='Text file with issue URLs or numbers (one per line)')
    parser.add_argument('-o', '--output', help='Output JSON file (optional)')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    fetch_issues_from_file(args.input, args.output)
