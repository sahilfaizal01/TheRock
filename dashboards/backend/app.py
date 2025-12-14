from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

from models.issue import (
    IssueAnalysis, AnalysisRequest, AnalysisResponse,
    IssueLabel, SimilarIssue, RootCauseCommit, ComponentCategory
)
from services.github_service import GitHubService
from services.ai_analyzer import AIAnalyzer
from services.git_tracer import GitTracer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TheRock Issue Analysis Dashboard",
    description="AI-powered issue analysis and root cause detection for ROCm/TheRock",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
github_service = None
ai_analyzer = None
git_tracer = None


def get_services():
    """Lazy initialization of services"""
    global github_service, ai_analyzer, git_tracer

    if github_service is None:
        github_service = GitHubService()
        logger.info("GitHub service initialized")

    if ai_analyzer is None:
        ai_analyzer = AIAnalyzer()
        logger.info("AI analyzer initialized")

    if git_tracer is None:
        git_tracer = GitTracer()
        logger.info("Git tracer initialized")

    return github_service, ai_analyzer, git_tracer


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TheRock Issue Analysis Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "issues": "/api/issues",
            "analyze": "/api/analyze",
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "github": os.getenv("GITHUB_TOKEN") is not None,
            "anthropic": os.getenv("ANTHROPIC_API_KEY") is not None
        }
    }


@app.get("/api/issues", response_model=List[Dict[str, Any]])
async def get_issues(limit: int = 20, state: str = "open"):
    """Get issues from the repository"""
    try:
        gh_service, _, _ = get_services()

        if state == "open":
            issues = gh_service.get_open_issues(limit=limit)
        elif state == "closed":
            issues = gh_service.get_closed_issues(limit=limit)
        else:
            raise HTTPException(status_code=400, detail="State must be 'open' or 'closed'")

        return issues

    except Exception as e:
        logger.error(f"Error fetching issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/issues/{issue_number}")
async def get_issue(issue_number: int):
    """Get a specific issue by number"""
    try:
        gh_service, _, _ = get_services()
        issue = gh_service.get_issue_by_number(issue_number)
        return issue

    except Exception as e:
        logger.error(f"Error fetching issue #{issue_number}: {e}")
        raise HTTPException(status_code=404, detail=f"Issue #{issue_number} not found")


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_issues(request: AnalysisRequest):
    """
    Analyze issues using AI
    - Categorize by ROCm component
    - Find similar historical issues
    - Identify root cause commits
    - Generate fix suggestions
    """
    try:
        gh_service, analyzer, tracer = get_services()

        # Fetch issues to analyze
        if request.analyze_all_open:
            issues = gh_service.get_open_issues(limit=request.limit)
        elif request.issue_numbers:
            issues = [gh_service.get_issue_by_number(num) for num in request.issue_numbers]
        else:
            raise HTTPException(status_code=400, detail="Must specify issue_numbers or analyze_all_open=true")

        # Fetch closed issues for similarity matching
        logger.info("Fetching closed issues for similarity matching...")
        closed_issues = gh_service.get_closed_issues(days=180, limit=200)

        # Fetch recent commits for root cause analysis
        logger.info("Fetching recent commits for root cause analysis...")
        since_date = datetime.now()
        if issues:
            # Use oldest issue creation date
            since_date = min(issue['created_at'] for issue in issues)

        recent_commits = gh_service.get_commits_since(since_date)

        # Analyze each issue
        analyses = []
        for issue in issues:
            logger.info(f"Analyzing issue #{issue['number']}: {issue['title']}")

            try:
                # Perform AI analysis
                analysis_result = analyzer.analyze_issue(issue, closed_issues, recent_commits)

                # Build IssueAnalysis object
                issue_analysis = IssueAnalysis(
                    issue_number=issue['number'],
                    title=issue['title'],
                    body=issue['body'],
                    created_at=issue['created_at'],
                    state=issue['state'],
                    url=issue['url'],
                    labels=[
                        IssueLabel(
                            name=label['name'],
                            color=label['color'],
                            description=label.get('description')
                        ) for label in issue['labels']
                    ],
                    component_categories=[
                        ComponentCategory(**cat) for cat in analysis_result['component_categories']
                    ],
                    similar_issues=[
                        SimilarIssue(**sim) for sim in analysis_result['similar_issues']
                    ],
                    root_cause_commits=[
                        RootCauseCommit(**commit) for commit in analysis_result['root_cause_commits']
                    ],
                    suggested_labels=analysis_result['suggested_labels'],
                    fix_suggestions=analysis_result['fix_suggestions'],
                    analysis_summary=analysis_result['analysis_summary'],
                    severity=analysis_result['severity']
                )

                analyses.append(issue_analysis)

            except Exception as e:
                logger.error(f"Error analyzing issue #{issue['number']}: {e}")
                continue

        response = AnalysisResponse(
            analyses=analyses,
            total_analyzed=len(analyses),
            timestamp=datetime.now()
        )

        return response

    except Exception as e:
        logger.error(f"Error in analyze endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/issues/{issue_number}/add-labels")
async def add_labels_to_issue(issue_number: int, labels: List[str]):
    """Add labels to an issue"""
    try:
        gh_service, _, _ = get_services()

        # Create labels if they don't exist
        for label in labels:
            gh_service.create_label_if_not_exists(label)

        # Add labels to issue
        for label in labels:
            gh_service.add_label_to_issue(issue_number, label)

        return {"status": "success", "issue_number": issue_number, "labels_added": labels}

    except Exception as e:
        logger.error(f"Error adding labels to issue #{issue_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/commits/recent")
async def get_recent_commits(days: int = 30, limit: int = 50):
    """Get recent commits from the repository"""
    try:
        gh_service, _, _ = get_services()

        since_date = datetime.now()
        commits = gh_service.get_commits_since(since_date, limit=limit)

        return commits

    except Exception as e:
        logger.error(f"Error fetching commits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/blame/{file_path:path}")
async def git_blame(file_path: str):
    """Git blame for a specific file"""
    try:
        _, _, tracer = get_services()

        blame_data = tracer.blame_file(file_path)
        return blame_data

    except Exception as e:
        logger.error(f"Error running git blame on {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    try:
        gh_service, _, _ = get_services()

        open_issues = gh_service.get_open_issues(limit=100)
        closed_issues = gh_service.get_closed_issues(days=30, limit=100)

        # Count issues by component (simplified)
        component_counts = {}

        return {
            "total_open_issues": len(open_issues),
            "total_closed_last_30_days": len(closed_issues),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
