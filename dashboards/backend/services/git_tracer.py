import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import git
from git import Repo, Commit
import logging

logger = logging.getLogger(__name__)


class GitTracer:
    """Service for tracing commits and finding root causes in git history"""

    def __init__(self, repo_path: str = "/home/user/TheRock"):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)

    def find_commits_affecting_paths(
        self,
        paths: List[str],
        since_date: Optional[datetime] = None,
        max_commits: int = 50
    ) -> List[Dict[str, Any]]:
        """Find commits that modified specific paths"""
        try:
            commits_data = []

            if since_date is None:
                since_date = datetime.now() - timedelta(days=90)

            # Get commits that touched the specified paths
            for path in paths:
                if not os.path.exists(os.path.join(self.repo_path, path)):
                    continue

                commits = list(self.repo.iter_commits(
                    paths=path,
                    since=since_date,
                    max_count=max_commits
                ))

                for commit in commits:
                    commit_data = self._commit_to_dict(commit)
                    commit_data['affected_path'] = path

                    if commit_data not in commits_data:
                        commits_data.append(commit_data)

            # Sort by date (most recent first)
            commits_data.sort(key=lambda x: x['date'], reverse=True)

            return commits_data[:max_commits]

        except Exception as e:
            logger.error(f"Error finding commits for paths {paths}: {e}")
            return []

    def find_commits_by_keyword(
        self,
        keywords: List[str],
        since_date: Optional[datetime] = None,
        max_commits: int = 50
    ) -> List[Dict[str, Any]]:
        """Find commits with specific keywords in the message"""
        try:
            if since_date is None:
                since_date = datetime.now() - timedelta(days=90)

            commits = list(self.repo.iter_commits(
                since=since_date,
                max_count=500
            ))

            matching_commits = []
            for commit in commits:
                message = commit.message.lower()

                # Check if any keyword is in the commit message
                if any(keyword.lower() in message for keyword in keywords):
                    matching_commits.append(self._commit_to_dict(commit))

                if len(matching_commits) >= max_commits:
                    break

            return matching_commits

        except Exception as e:
            logger.error(f"Error finding commits by keywords {keywords}: {e}")
            return []

    def blame_file(self, file_path: str, line_numbers: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Git blame for a specific file (or specific lines)"""
        try:
            full_path = os.path.join(self.repo_path, file_path)

            if not os.path.exists(full_path):
                return []

            blame_data = []

            # Get blame for the file
            blame_list = self.repo.blame('HEAD', file_path)

            for commit, lines in blame_list:
                if line_numbers:
                    # Filter only requested line numbers
                    # Note: This is simplified; a full implementation would track line numbers
                    pass

                blame_data.append({
                    'commit': self._commit_to_dict(commit),
                    'lines_count': len(lines)
                })

            # Group by commit and count lines
            commit_impact = {}
            for item in blame_data:
                sha = item['commit']['sha']
                if sha in commit_impact:
                    commit_impact[sha]['lines_count'] += item['lines_count']
                else:
                    commit_impact[sha] = item['commit']
                    commit_impact[sha]['lines_count'] = item['lines_count']

            # Sort by lines count (commits affecting most lines first)
            result = sorted(commit_impact.values(), key=lambda x: x['lines_count'], reverse=True)

            return result

        except Exception as e:
            logger.error(f"Error blaming file {file_path}: {e}")
            return []

    def find_breaking_commits(
        self,
        component_paths: List[str],
        error_keywords: List[str],
        since_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Find commits that likely introduced a breakage based on:
        1. Commits affecting specific component paths
        2. Commits with error-related keywords
        """
        try:
            if since_date is None:
                since_date = datetime.now() - timedelta(days=60)

            # Find commits affecting the component
            path_commits = self.find_commits_affecting_paths(component_paths, since_date, max_commits=30)

            # Find commits with error keywords
            keyword_commits = self.find_commits_by_keyword(error_keywords, since_date, max_commits=30)

            # Combine and deduplicate
            all_commits = {}
            for commit in path_commits + keyword_commits:
                sha = commit['sha']
                if sha not in all_commits:
                    all_commits[sha] = commit
                    all_commits[sha]['confidence_score'] = 0.0

                # Increase confidence if in both lists
                if sha in [c['sha'] for c in path_commits]:
                    all_commits[sha]['confidence_score'] += 0.5

                if sha in [c['sha'] for c in keyword_commits]:
                    all_commits[sha]['confidence_score'] += 0.3

            # Sort by confidence score
            result = sorted(all_commits.values(), key=lambda x: x['confidence_score'], reverse=True)

            return result[:10]

        except Exception as e:
            logger.error(f"Error finding breaking commits: {e}")
            return []

    def get_file_history(self, file_path: str, max_commits: int = 20) -> List[Dict[str, Any]]:
        """Get the commit history for a specific file"""
        try:
            commits = list(self.repo.iter_commits(paths=file_path, max_count=max_commits))
            return [self._commit_to_dict(commit) for commit in commits]

        except Exception as e:
            logger.error(f"Error getting file history for {file_path}: {e}")
            return []

    def get_commit_diff(self, commit_sha: str) -> Dict[str, Any]:
        """Get the diff for a specific commit"""
        try:
            commit = self.repo.commit(commit_sha)

            # Get parent (previous commit)
            if commit.parents:
                parent = commit.parents[0]
                diff = parent.diff(commit, create_patch=True)
            else:
                # First commit has no parent
                diff = commit.diff(git.NULL_TREE, create_patch=True)

            diff_data = []
            for diff_item in diff:
                diff_data.append({
                    'file_path': diff_item.a_path or diff_item.b_path,
                    'change_type': diff_item.change_type,
                    'diff': diff_item.diff.decode('utf-8', errors='ignore') if diff_item.diff else ""
                })

            return {
                'commit': self._commit_to_dict(commit),
                'diffs': diff_data
            }

        except Exception as e:
            logger.error(f"Error getting diff for commit {commit_sha}: {e}")
            return {'commit': {}, 'diffs': []}

    def extract_file_paths_from_error(self, error_text: str) -> List[str]:
        """Extract potential file paths from error messages"""
        # Common patterns for file paths in error messages
        patterns = [
            r'(?:File|file|at)\s+"?([a-zA-Z0-9_/\.\-]+\.[a-zA-Z0-9]+)"?',
            r'([a-zA-Z0-9_/\-]+/[a-zA-Z0-9_/\.\-]+)',
            r'\b([a-z_]+/[a-z_]+\.(?:py|cpp|h|hpp|c|cmake|sh))\b'
        ]

        file_paths = set()
        for pattern in patterns:
            matches = re.findall(pattern, error_text, re.IGNORECASE)
            file_paths.update(matches)

        # Filter to only include paths that exist in the repo
        existing_paths = []
        for path in file_paths:
            if os.path.exists(os.path.join(self.repo_path, path)):
                existing_paths.append(path)

        return existing_paths

    def _commit_to_dict(self, commit: Commit) -> Dict[str, Any]:
        """Convert a GitPython commit object to a dictionary"""
        return {
            'sha': commit.hexsha,
            'short_sha': commit.hexsha[:7],
            'message': commit.message.strip(),
            'author': commit.author.name,
            'author_email': commit.author.email,
            'date': datetime.fromtimestamp(commit.committed_date),
            'url': f"https://github.com/ROCm/TheRock/commit/{commit.hexsha}",
            'files_changed': list(commit.stats.files.keys()) if commit.stats else []
        }
