import os
from typing import List, Dict, Any, Optional
import anthropic
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import json

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI-powered issue analyzer using Claude API"""

    # ROCm component categorization based on TheRock repository structure
    ROCM_COMPONENTS = {
        "compiler": ["llvm", "hip", "hipify", "compiler", "clang", "spirv", "device code", "kernel compilation"],
        "runtime": ["hip runtime", "runtime", "device management", "memory management", "streams", "events"],
        "math-libs": ["rocblas", "blas", "linear algebra", "rocsolver", "rocfft", "fft", "rocrand", "random"],
        "ml-libs": ["miopen", "composable kernel", "rocal", "machine learning", "neural network", "deep learning"],
        "comm-libs": ["rccl", "communication", "collective", "nccl", "mpi"],
        "profiler": ["rocprof", "profiler", "profiling", "trace", "performance analysis"],
        "pytorch": ["pytorch", "torch", "torchvision", "training", "inference"],
        "build-system": ["cmake", "build", "compilation", "linking", "makefile", "ninja"],
        "packaging": ["package", "install", "rpm", "deb", "wheel", "pip", "apt"],
        "ci-cd": ["github actions", "workflow", "ci", "cd", "pipeline", "test harness"],
        "gpu-arch": ["gfx", "gfx94", "gfx110", "gfx120", "gfx950", "mi", "architecture", "vega", "navi"],
        "core": ["rocm-core", "amdsmi", "smi", "device query", "system management"],
        "base": ["half", "rocm-cmake", "base libraries"]
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_issue(
        self,
        issue: Dict[str, Any],
        closed_issues: List[Dict[str, Any]],
        recent_commits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive AI analysis of an issue:
        1. Categorize by ROCm component
        2. Find similar historical issues
        3. Identify potential root cause commits
        4. Generate fix suggestions
        """

        # Step 1: Component categorization
        component_categories = self._categorize_components(issue)

        # Step 2: Find similar issues
        similar_issues = self._find_similar_issues(issue, closed_issues)

        # Step 3: Analyze severity and get AI insights
        ai_insights = self._get_claude_analysis(issue, component_categories, similar_issues)

        # Step 4: Identify potential root cause commits
        root_cause_commits = self._identify_root_cause_commits(issue, recent_commits, component_categories)

        # Step 5: Generate suggested labels
        suggested_labels = self._generate_labels(component_categories, ai_insights)

        return {
            'component_categories': component_categories,
            'similar_issues': similar_issues,
            'root_cause_commits': root_cause_commits,
            'suggested_labels': suggested_labels,
            'fix_suggestions': ai_insights.get('fix_suggestions', []),
            'analysis_summary': ai_insights.get('summary', ''),
            'severity': ai_insights.get('severity', 'medium')
        }

    def _categorize_components(self, issue: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Categorize issue by ROCm components using keyword matching and AI"""

        text = f"{issue['title']} {issue['body']}".lower()

        categories = []
        for component, keywords in self.ROCM_COMPONENTS.items():
            # Count keyword matches
            matches = sum(1 for keyword in keywords if keyword.lower() in text)

            if matches > 0:
                confidence = min(matches / len(keywords) * 2, 1.0)  # Scale to 0-1

                categories.append({
                    'component': component,
                    'confidence': round(confidence, 2),
                    'reasoning': f"Matched {matches} keywords: {[k for k in keywords if k.lower() in text][:3]}"
                })

        # Sort by confidence
        categories.sort(key=lambda x: x['confidence'], reverse=True)

        return categories[:3]  # Return top 3

    def _find_similar_issues(
        self,
        issue: Dict[str, Any],
        closed_issues: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar historical issues using TF-IDF similarity"""

        if not closed_issues:
            return []

        try:
            # Prepare texts
            current_text = f"{issue['title']} {issue['body']}"
            closed_texts = [f"{i['title']} {i['body']}" for i in closed_issues]

            all_texts = [current_text] + closed_texts

            # Calculate TF-IDF vectors
            vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(all_texts)

            # Calculate similarity
            current_vector = tfidf_matrix[0:1]
            closed_vectors = tfidf_matrix[1:]

            similarities = cosine_similarity(current_vector, closed_vectors)[0]

            # Get top K similar issues
            similar_indices = similarities.argsort()[-top_k:][::-1]

            similar_issues = []
            for idx in similar_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    similar_issues.append({
                        'number': closed_issues[idx]['number'],
                        'title': closed_issues[idx]['title'],
                        'url': closed_issues[idx]['url'],
                        'state': closed_issues[idx]['state'],
                        'similarity_score': round(float(similarities[idx]), 3),
                        'closed_at': closed_issues[idx].get('closed_at')
                    })

            return similar_issues

        except Exception as e:
            logger.error(f"Error finding similar issues: {e}")
            return []

    def _get_claude_analysis(
        self,
        issue: Dict[str, Any],
        component_categories: List[Dict[str, Any]],
        similar_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use Claude API to get deeper analysis and suggestions"""

        try:
            # Prepare context
            components_str = ", ".join([c['component'] for c in component_categories[:3]])
            similar_str = "\n".join([f"- #{i['number']}: {i['title']}" for i in similar_issues[:3]])

            prompt = f"""Analyze this GitHub issue from the ROCm/TheRock repository:

**Issue #{issue['number']}: {issue['title']}**

**Description:**
{issue['body'][:1500]}

**Detected Components:** {components_str or 'Unknown'}

**Similar Historical Issues:**
{similar_str or 'None found'}

Please provide:
1. **Severity** (critical/high/medium/low) - Consider impact on users
2. **Analysis Summary** (2-3 sentences) - What is the core problem?
3. **Fix Suggestions** (3-5 actionable items) - Specific steps to resolve this

Respond in JSON format:
{{
  "severity": "...",
  "summary": "...",
  "fix_suggestions": ["...", "...", "..."]
}}"""

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = message.content[0].text

            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response_text[json_start:json_end])
                return analysis
            else:
                logger.warning("Claude response was not in JSON format")
                return {
                    'severity': 'medium',
                    'summary': response_text[:200],
                    'fix_suggestions': []
                }

        except Exception as e:
            logger.error(f"Error getting Claude analysis: {e}")
            return {
                'severity': 'medium',
                'summary': f'Automated analysis unavailable: {str(e)}',
                'fix_suggestions': []
            }

    def _identify_root_cause_commits(
        self,
        issue: Dict[str, Any],
        recent_commits: List[Dict[str, Any]],
        component_categories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify commits that potentially caused the issue"""

        if not recent_commits:
            return []

        # Extract relevant keywords from issue
        text = f"{issue['title']} {issue['body']}".lower()
        error_keywords = ['error', 'fail', 'crash', 'bug', 'broken', 'regression']

        # Get component paths
        component_paths = []
        for cat in component_categories[:2]:
            component = cat['component']
            # Map component to directory paths
            if component in ['compiler', 'llvm', 'hip']:
                component_paths.append('compiler/')
            elif component in ['runtime']:
                component_paths.append('core/')
            elif component in ['math-libs']:
                component_paths.append('math-libs/')
            elif component in ['ml-libs']:
                component_paths.append('ml-libs/')
            elif component in ['pytorch']:
                component_paths.append('external-builds/pytorch/')
            elif component in ['build-system']:
                component_paths.append('cmake/')
            elif component in ['ci-cd']:
                component_paths.append('.github/')

        suspect_commits = []
        for commit in recent_commits[:50]:
            confidence = 0.0

            # Check if commit touches relevant component paths
            for file in commit.get('files_changed', []):
                if any(file.startswith(path) for path in component_paths):
                    confidence += 0.3

            # Check if commit message mentions error keywords
            message = commit['message'].lower()
            if any(keyword in message for keyword in error_keywords):
                confidence += 0.2

            # Check if commit is recent (within 30 days of issue creation)
            if 'created_at' in issue and 'date' in commit:
                # Simple heuristic: more recent commits are more likely
                confidence += 0.1

            if confidence > 0.2:
                commit_data = commit.copy()
                commit_data['confidence_score'] = round(confidence, 2)
                suspect_commits.append(commit_data)

        # Sort by confidence
        suspect_commits.sort(key=lambda x: x['confidence_score'], reverse=True)

        return suspect_commits[:5]

    def _generate_labels(
        self,
        component_categories: List[Dict[str, Any]],
        ai_insights: Dict[str, Any]
    ) -> List[str]:
        """Generate suggested labels for the issue"""

        labels = []

        # Add component labels
        for cat in component_categories[:2]:
            if cat['confidence'] > 0.3:
                labels.append(f"component:{cat['component']}")

        # Add severity label
        severity = ai_insights.get('severity', 'medium')
        labels.append(f"severity:{severity}")

        # Add type label (inferred from keywords)
        labels.append("type:bug")

        return labels
