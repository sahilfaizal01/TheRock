import os
from typing import List, Optional, Dict, Any
from github import Github, GithubException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API"""

    def __init__(self, token: Optional[str] = None, repo_owner: str = "ROCm", repo_name: str = "TheRock"):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github = Github(self.token)
        self.repo = self.github.get_repo(f"{repo_owner}/{repo_name}")

    def get_open_issues(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch open issues from the repository"""
        try:
            issues = self.repo.get_issues(state='open', sort='created', direction='desc')

            result = []
            for issue in issues[:limit]:
                # Skip pull requests (they also appear in issues API)
                if issue.pull_request:
                    continue

                result.append({
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body or "",
                    'state': issue.state,
                    'url': issue.html_url,
                    'created_at': issue.created_at,
                    'updated_at': issue.updated_at,
                    'labels': [{'name': label.name, 'color': label.color, 'description': label.description}
                              for label in issue.labels],
                    'assignees': [assignee.login for assignee in issue.assignees],
                    'comments_count': issue.comments,
                    'author': issue.user.login if issue.user else "unknown"
                })

            logger.info(f"Fetched {len(result)} open issues")
            return result

        except GithubException as e:
            logger.error(f"Error fetching issues: {e}")
            raise

    def get_issue_by_number(self, issue_number: int) -> Dict[str, Any]:
        """Fetch a specific issue by number"""
        try:
            issue = self.repo.get_issue(issue_number)

            return {
                'number': issue.number,
                'title': issue.title,
                'body': issue.body or "",
                'state': issue.state,
                'url': issue.html_url,
                'created_at': issue.created_at,
                'updated_at': issue.updated_at,
                'labels': [{'name': label.name, 'color': label.color, 'description': label.description}
                          for label in issue.labels],
                'assignees': [assignee.login for assignee in issue.assignees],
                'comments_count': issue.comments,
                'author': issue.user.login if issue.user else "unknown"
            }

        except GithubException as e:
            logger.error(f"Error fetching issue #{issue_number}: {e}")
            raise

    def get_closed_issues(self, days: int = 180, limit: int = 200) -> List[Dict[str, Any]]:
        """Fetch recently closed issues for similarity matching"""
        try:
            since_date = datetime.now() - timedelta(days=days)
            issues = self.repo.get_issues(state='closed', sort='updated', direction='desc', since=since_date)

            result = []
            for issue in issues[:limit]:
                if issue.pull_request:
                    continue

                result.append({
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body or "",
                    'state': issue.state,
                    'url': issue.html_url,
                    'created_at': issue.created_at,
                    'closed_at': issue.closed_at,
                    'labels': [label.name for label in issue.labels],
                })

            logger.info(f"Fetched {len(result)} closed issues from last {days} days")
            return result

        except GithubException as e:
            logger.error(f"Error fetching closed issues: {e}")
            raise

    def get_commits_since(self, since_date: datetime, until_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get commits in a date range"""
        try:
            commits = self.repo.get_commits(since=since_date, until=until_date)

            result = []
            for commit in commits[:500]:  # Limit to prevent rate limiting
                result.append({
                    'sha': commit.sha,
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date,
                    'url': commit.html_url,
                    'files_changed': [f.filename for f in commit.files] if commit.files else []
                })

            return result

        except GithubException as e:
            logger.error(f"Error fetching commits: {e}")
            raise

    def get_pull_request_for_commit(self, commit_sha: str) -> Optional[Dict[str, Any]]:
        """Find the PR that introduced a specific commit"""
        try:
            # Search for PRs that contain this commit
            prs = self.repo.get_pulls(state='closed', sort='updated', direction='desc')

            for pr in prs[:100]:  # Check last 100 PRs
                if pr.merge_commit_sha == commit_sha:
                    return {
                        'number': pr.number,
                        'title': pr.title,
                        'url': pr.html_url,
                        'merged_at': pr.merged_at,
                        'author': pr.user.login if pr.user else "unknown"
                    }

            return None

        except GithubException as e:
            logger.error(f"Error finding PR for commit {commit_sha}: {e}")
            return None

    def add_label_to_issue(self, issue_number: int, label: str) -> bool:
        """Add a label to an issue"""
        try:
            issue = self.repo.get_issue(issue_number)
            issue.add_to_labels(label)
            logger.info(f"Added label '{label}' to issue #{issue_number}")
            return True

        except GithubException as e:
            logger.error(f"Error adding label to issue #{issue_number}: {e}")
            return False

    def create_label_if_not_exists(self, name: str, color: str = "0366d6", description: str = "") -> bool:
        """Create a label if it doesn't exist"""
        try:
            # Check if label exists
            try:
                self.repo.get_label(name)
                return True
            except GithubException:
                # Label doesn't exist, create it
                self.repo.create_label(name=name, color=color, description=description)
                logger.info(f"Created label '{name}'")
                return True

        except GithubException as e:
            logger.error(f"Error creating label '{name}': {e}")
            return False

    def get_issue_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """Get all comments for an issue"""
        try:
            issue = self.repo.get_issue(issue_number)
            comments = issue.get_comments()

            return [{
                'author': comment.user.login if comment.user else "unknown",
                'body': comment.body,
                'created_at': comment.created_at
            } for comment in comments]

        except GithubException as e:
            logger.error(f"Error fetching comments for issue #{issue_number}: {e}")
            return []
