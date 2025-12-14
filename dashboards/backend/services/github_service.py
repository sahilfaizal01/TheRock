import os
import json
from typing import List, Optional, Dict, Any
from github import Github, GithubException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import cache service
try:
    from .cache_service import CacheService
except ImportError:
    CacheService = None


class GitHubService:
    """Service for interacting with GitHub API"""

    def __init__(self, token: Optional[str] = None, repo_owner: str = "ROCm", repo_name: str = "TheRock", use_cache: bool = True):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo_owner = repo_owner
        self.repo_name = repo_name

        # Check for offline mode
        self.offline_file = os.getenv("OFFLINE_ISSUES_FILE")
        if self.offline_file:
            logger.info(f"Offline mode enabled: using {self.offline_file}")
            self.github = None
            self.repo = None
        else:
            self.github = Github(self.token)
            self.repo = self.github.get_repo(f"{repo_owner}/{repo_name}")

        # Initialize cache
        self.cache = CacheService() if use_cache and CacheService else None
        if self.cache:
            logger.info("GitHub service initialized with caching enabled")

    def _load_from_offline_file(self) -> Optional[Dict[str, Any]]:
        """Load issues from offline JSON file"""
        if not self.offline_file:
            return None

        try:
            # Handle relative paths
            if not os.path.isabs(self.offline_file):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                offline_path = os.path.join(base_dir, '..', self.offline_file)
            else:
                offline_path = self.offline_file

            logger.info(f"Loading issues from offline file: {offline_path}")

            with open(offline_path, 'r') as f:
                data = json.load(f)

            # Handle different JSON structures
            if 'issues' in data:
                return data['issues']
            elif isinstance(data, list):
                return data
            else:
                return None

        except Exception as e:
            logger.error(f"Error loading offline file: {e}")
            return None

    def get_open_issues(self, limit: int = 100, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch open issues from the repository"""

        # Check offline mode first
        if self.offline_file:
            offline_data = self._load_from_offline_file()
            if offline_data:
                logger.info(f"Loaded {len(offline_data)} issues from offline file")
                return offline_data[:limit]
            else:
                logger.warning("Failed to load from offline file, falling back to API")

        cache_key = f"open_issues_{self.repo_owner}_{self.repo_name}_{limit}"

        # Try cache first
        if self.cache and not force_refresh:
            cached_data = self.cache.get(cache_key, max_age_hours=1)  # Cache for 1 hour
            if cached_data:
                return cached_data

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

            logger.info(f"Fetched {len(result)} open issues from API")

            # Cache the results
            if self.cache:
                self.cache.set(cache_key, result)

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

    def get_closed_issues(self, days: int = 180, limit: int = 200, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch recently closed issues for similarity matching"""

        # Check offline mode first
        if self.offline_file:
            offline_data = self._load_from_offline_file()
            if offline_data:
                # Filter for closed issues if available
                closed = [i for i in offline_data if i.get('state') == 'closed']
                if closed:
                    logger.info(f"Loaded {len(closed)} closed issues from offline file")
                    return closed[:limit]
                else:
                    # No closed issues in file, return empty or all issues
                    logger.warning("No closed issues in offline file")
                    return []

        cache_key = f"closed_issues_{self.repo_owner}_{self.repo_name}_{days}_{limit}"

        # Try cache first (cache for 24 hours since closed issues don't change often)
        if self.cache and not force_refresh:
            cached_data = self.cache.get(cache_key, max_age_hours=24)
            if cached_data:
                return cached_data

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

            logger.info(f"Fetched {len(result)} closed issues from last {days} days from API")

            # Cache the results
            if self.cache:
                self.cache.set(cache_key, result)

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
