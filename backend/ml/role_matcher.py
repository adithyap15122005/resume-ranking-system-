"""
Role Matching Engine for Production ATS

Detects primary roles from resume/job text and computes role similarity scores.
This ensures Cloud Engineers don't score 85% for Data Scientist jobs.
"""

from typing import Dict, List, Tuple, Optional
import re
from collections import Counter


# Role taxonomy with keywords and patterns
ROLE_TAXONOMY = {
    "Cloud Engineer": {
        "keywords": ["cloud engineer", "cloud architect", "solutions architect", "cloud specialist"],
        "tech": ["aws", "azure", "gcp", "cloud", "iaas", "paas", "ec2", "s3", "lambda"],
        "domain": "cloud"
    },
    "DevOps Engineer": {
        "keywords": ["devops", "sre", "site reliability", "platform engineer", "infrastructure engineer"],
        "tech": ["docker", "kubernetes", "jenkins", "ci/cd", "terraform", "ansible", "gitlab", "circleci"],
        "domain": "devops"
    },
    "Backend Developer": {
        "keywords": ["backend", "backend developer", "backend engineer", "api developer", "server-side"],
        "tech": ["python", "java", "node.js", "fastapi", "django", "spring", "express", "rest", "graphql"],
        "domain": "backend"
    },
    "Frontend Developer": {
        "keywords": ["frontend", "front-end", "ui developer", "web developer"],
        "tech": ["react", "angular", "vue", "javascript", "typescript", "html", "css", "next.js", "svelte"],
        "domain": "frontend"
    },
    "Full Stack Developer": {
        "keywords": ["full stack", "fullstack", "full-stack"],
        "tech": ["react", "node", "mongodb", "mern", "mean", "django", "flask"],
        "domain": "fullstack"
    },
    "Software Engineer": {
        "keywords": ["software engineer", "software developer", "programmer"],
        "tech": ["programming", "coding", "algorithms", "data structures"],
        "domain": "software"
    },
    "Machine Learning Engineer": {
        "keywords": ["machine learning engineer", "ml engineer", "mlops"],
        "tech": ["tensorflow", "pytorch", "keras", "ml", "neural network", "deep learning", "model deployment"],
        "domain": "ml"
    },
    "Data Scientist": {
        "keywords": ["data scientist", "data analytics", "statistician"],
        "tech": ["pandas", "numpy", "statistics", "scikit-learn", "matplotlib", "jupyter", "r", "analysis"],
        "domain": "data_science"
    },
    "Data Engineer": {
        "keywords": ["data engineer", "etl developer", "data pipeline"],
        "tech": ["spark", "kafka", "airflow", "hadoop", "hive", "snowflake", "databricks", "etl"],
        "domain": "data_engineering"
    },
    "AI Engineer": {
        "keywords": ["ai engineer", "artificial intelligence"],
        "tech": ["ai", "nlp", "computer vision", "llm", "gpt", "transformers", "openai"],
        "domain": "ai"
    },
    "QA Engineer": {
        "keywords": ["qa engineer", "quality assurance", "test engineer", "sdet", "automation engineer"],
        "tech": ["selenium", "junit", "pytest", "cypress", "playwright", "testing", "automation"],
        "domain": "qa"
    },
    "Security Engineer": {
        "keywords": ["security engineer", "infosec", "cybersecurity", "appsec", "devsecops"],
        "tech": ["siem", "penetration testing", "security", "iam", "firewall", "vulnerability", "owasp"],
        "domain": "security"
    },
    "Product Manager": {
        "keywords": ["product manager", "pm", "product owner", "program manager"],
        "tech": ["roadmap", "stakeholder", "agile", "scrum", "jira", "product strategy"],
        "domain": "product"
    },
    "Mobile Developer": {
        "keywords": ["mobile developer", "ios developer", "android developer", "mobile engineer"],
        "tech": ["swift", "kotlin", "react native", "flutter", "ios", "android", "xcode"],
        "domain": "mobile"
    },
}


# Role similarity matrix (0.0 = completely different, 1.0 = identical)
# This defines how similar roles are to each other
ROLE_SIMILARITY_MATRIX = {
    ("Cloud Engineer", "Cloud Engineer"): 1.0,
    ("Cloud Engineer", "DevOps Engineer"): 0.85,
    ("Cloud Engineer", "Backend Developer"): 0.45,
    ("Cloud Engineer", "Full Stack Developer"): 0.35,
    ("Cloud Engineer", "Software Engineer"): 0.40,
    ("Cloud Engineer", "Data Scientist"): 0.15,
    ("Cloud Engineer", "Data Engineer"): 0.30,
    ("Cloud Engineer", "Machine Learning Engineer"): 0.20,
    ("Cloud Engineer", "AI Engineer"): 0.20,
    ("Cloud Engineer", "QA Engineer"): 0.25,
    ("Cloud Engineer", "Security Engineer"): 0.50,
    ("Cloud Engineer", "Frontend Developer"): 0.25,
    ("Cloud Engineer", "Product Manager"): 0.10,
    ("Cloud Engineer", "Mobile Developer"): 0.20,

    ("DevOps Engineer", "DevOps Engineer"): 1.0,
    ("DevOps Engineer", "Cloud Engineer"): 0.85,
    ("DevOps Engineer", "Backend Developer"): 0.55,
    ("DevOps Engineer", "Software Engineer"): 0.45,
    ("DevOps Engineer", "Full Stack Developer"): 0.40,
    ("DevOps Engineer", "Data Engineer"): 0.40,
    ("DevOps Engineer", "Security Engineer"): 0.60,
    ("DevOps Engineer", "QA Engineer"): 0.35,
    ("DevOps Engineer", "Data Scientist"): 0.20,
    ("DevOps Engineer", "Machine Learning Engineer"): 0.25,
    ("DevOps Engineer", "Frontend Developer"): 0.30,
    ("DevOps Engineer", "Product Manager"): 0.10,

    ("Backend Developer", "Backend Developer"): 1.0,
    ("Backend Developer", "Full Stack Developer"): 0.85,
    ("Backend Developer", "Software Engineer"): 0.75,
    ("Backend Developer", "DevOps Engineer"): 0.55,
    ("Backend Developer", "Cloud Engineer"): 0.45,
    ("Backend Developer", "Data Engineer"): 0.50,
    ("Backend Developer", "Machine Learning Engineer"): 0.40,
    ("Backend Developer", "Frontend Developer"): 0.50,
    ("Backend Developer", "Data Scientist"): 0.25,
    ("Backend Developer", "QA Engineer"): 0.40,
    ("Backend Developer", "Security Engineer"): 0.45,
    ("Backend Developer", "Mobile Developer"): 0.35,

    ("Frontend Developer", "Frontend Developer"): 1.0,
    ("Frontend Developer", "Full Stack Developer"): 0.85,
    ("Frontend Developer", "Software Engineer"): 0.65,
    ("Frontend Developer", "Backend Developer"): 0.50,
    ("Frontend Developer", "Mobile Developer"): 0.60,
    ("Frontend Developer", "DevOps Engineer"): 0.30,
    ("Frontend Developer", "Cloud Engineer"): 0.25,
    ("Frontend Developer", "Data Scientist"): 0.15,
    ("Frontend Developer", "QA Engineer"): 0.35,
    ("Frontend Developer", "Product Manager"): 0.15,

    ("Full Stack Developer", "Full Stack Developer"): 1.0,
    ("Full Stack Developer", "Backend Developer"): 0.85,
    ("Full Stack Developer", "Frontend Developer"): 0.85,
    ("Full Stack Developer", "Software Engineer"): 0.80,
    ("Full Stack Developer", "DevOps Engineer"): 0.40,
    ("Full Stack Developer", "Cloud Engineer"): 0.35,
    ("Full Stack Developer", "Mobile Developer"): 0.45,
    ("Full Stack Developer", "Data Engineer"): 0.35,

    ("Software Engineer", "Software Engineer"): 1.0,
    ("Software Engineer", "Backend Developer"): 0.75,
    ("Software Engineer", "Full Stack Developer"): 0.80,
    ("Software Engineer", "Frontend Developer"): 0.65,
    ("Software Engineer", "DevOps Engineer"): 0.45,
    ("Software Engineer", "Cloud Engineer"): 0.40,
    ("Software Engineer", "Data Engineer"): 0.50,
    ("Software Engineer", "Machine Learning Engineer"): 0.50,
    ("Software Engineer", "QA Engineer"): 0.45,

    ("Machine Learning Engineer", "Machine Learning Engineer"): 1.0,
    ("Machine Learning Engineer", "Data Scientist"): 0.90,
    ("Machine Learning Engineer", "AI Engineer"): 0.95,
    ("Machine Learning Engineer", "Data Engineer"): 0.60,
    ("Machine Learning Engineer", "Backend Developer"): 0.40,
    ("Machine Learning Engineer", "Software Engineer"): 0.50,
    ("Machine Learning Engineer", "Cloud Engineer"): 0.25,
    ("Machine Learning Engineer", "DevOps Engineer"): 0.25,
    ("Machine Learning Engineer", "QA Engineer"): 0.15,
    ("Machine Learning Engineer", "Frontend Developer"): 0.10,

    ("Data Scientist", "Data Scientist"): 1.0,
    ("Data Scientist", "Machine Learning Engineer"): 0.90,
    ("Data Scientist", "AI Engineer"): 0.85,
    ("Data Scientist", "Data Engineer"): 0.65,
    ("Data Scientist", "Backend Developer"): 0.25,
    ("Data Scientist", "Software Engineer"): 0.30,
    ("Data Scientist", "DevOps Engineer"): 0.20,
    ("Data Scientist", "Cloud Engineer"): 0.15,
    ("Data Scientist", "QA Engineer"): 0.10,
    ("Data Scientist", "Frontend Developer"): 0.15,

    ("Data Engineer", "Data Engineer"): 1.0,
    ("Data Engineer", "Data Scientist"): 0.65,
    ("Data Engineer", "Machine Learning Engineer"): 0.60,
    ("Data Engineer", "Backend Developer"): 0.50,
    ("Data Engineer", "DevOps Engineer"): 0.40,
    ("Data Engineer", "Cloud Engineer"): 0.30,
    ("Data Engineer", "Software Engineer"): 0.50,

    ("AI Engineer", "AI Engineer"): 1.0,
    ("AI Engineer", "Machine Learning Engineer"): 0.95,
    ("AI Engineer", "Data Scientist"): 0.85,
    ("AI Engineer", "Data Engineer"): 0.55,
    ("AI Engineer", "Backend Developer"): 0.35,
    ("AI Engineer", "Cloud Engineer"): 0.20,

    ("QA Engineer", "QA Engineer"): 1.0,
    ("QA Engineer", "Backend Developer"): 0.40,
    ("QA Engineer", "DevOps Engineer"): 0.35,
    ("QA Engineer", "Frontend Developer"): 0.35,
    ("QA Engineer", "Software Engineer"): 0.45,
    ("QA Engineer", "Cloud Engineer"): 0.25,
    ("QA Engineer", "Data Scientist"): 0.10,
    ("QA Engineer", "Machine Learning Engineer"): 0.15,
    ("QA Engineer", "Security Engineer"): 0.30,

    ("Security Engineer", "Security Engineer"): 1.0,
    ("Security Engineer", "DevOps Engineer"): 0.60,
    ("Security Engineer", "Cloud Engineer"): 0.50,
    ("Security Engineer", "Backend Developer"): 0.45,
    ("Security Engineer", "QA Engineer"): 0.30,
    ("Security Engineer", "Software Engineer"): 0.40,

    ("Product Manager", "Product Manager"): 1.0,
    ("Product Manager", "Software Engineer"): 0.20,
    ("Product Manager", "Backend Developer"): 0.15,
    ("Product Manager", "Frontend Developer"): 0.15,

    ("Mobile Developer", "Mobile Developer"): 1.0,
    ("Mobile Developer", "Frontend Developer"): 0.60,
    ("Mobile Developer", "Full Stack Developer"): 0.45,
    ("Mobile Developer", "Software Engineer"): 0.55,
    ("Mobile Developer", "Backend Developer"): 0.35,
}


class RoleMatcher:
    """Detects roles from text and computes role similarity scores."""

    def __init__(self):
        self.role_taxonomy = ROLE_TAXONOMY
        self.similarity_matrix = ROLE_SIMILARITY_MATRIX

    def detect_role(self, text: str, context: str = "resume") -> Tuple[Optional[str], float]:
        """
        Detect primary role from text.

        Args:
            text: Resume or job description text
            context: "resume" or "job" (for better heuristics)

        Returns:
            (role_name, confidence) or (None, 0.0) if no clear role
        """
        if not text:
            return None, 0.0

        text_lower = text.lower()
        role_scores = {}

        for role_name, role_data in self.role_taxonomy.items():
            score = 0.0

            # Check for exact role keyword matches
            for keyword in role_data["keywords"]:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = len(re.findall(pattern, text_lower))
                if matches > 0:
                    # First occurrence is strongest
                    score += 5.0 + min(matches - 1, 2) * 1.0

            # Check for technical terms (weaker signal)
            tech_matches = sum(1 for tech in role_data["tech"] if tech in text_lower)
            tech_score = min(tech_matches * 0.3, 3.0)
            score += tech_score

            role_scores[role_name] = score

        if not role_scores or max(role_scores.values()) < 1.0:
            return None, 0.0

        # Get top role
        top_role = max(role_scores.items(), key=lambda x: x[1])
        role_name, raw_score = top_role

        # Normalize confidence to [0, 1]
        confidence = min(raw_score / 10.0, 1.0)

        return role_name, confidence

    def get_role_similarity(self, role1: Optional[str], role2: Optional[str]) -> float:
        """
        Get similarity score between two roles.

        Args:
            role1: First role name (e.g., "Cloud Engineer")
            role2: Second role name (e.g., "Data Scientist")

        Returns:
            Similarity score [0.0, 1.0]
            1.0 = identical roles
            0.0 = completely unrelated
        """
        if not role1 or not role2:
            return 0.5  # Neutral if role unknown

        # Exact match
        if role1 == role2:
            return 1.0

        # Check forward direction
        key_forward = (role1, role2)
        if key_forward in self.similarity_matrix:
            return self.similarity_matrix[key_forward]

        # Check reverse direction
        key_reverse = (role2, role1)
        if key_reverse in self.similarity_matrix:
            return self.similarity_matrix[key_reverse]

        # Not in matrix — use domain heuristic
        domain1 = self.role_taxonomy.get(role1, {}).get("domain", "")
        domain2 = self.role_taxonomy.get(role2, {}).get("domain", "")

        if domain1 and domain2:
            if domain1 == domain2:
                return 0.70  # Same domain
            elif self._domains_related(domain1, domain2):
                return 0.40  # Related domains

        return 0.20  # Default low similarity for unknown pairs

    def _domains_related(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are related."""
        related_pairs = [
            {"cloud", "devops"},
            {"backend", "fullstack"},
            {"frontend", "fullstack"},
            {"ml", "ai"},
            {"ml", "data_science"},
            {"ai", "data_science"},
            {"data_science", "data_engineering"},
            {"backend", "software"},
            {"frontend", "software"},
        ]

        pair = {domain1, domain2}
        return pair in related_pairs

    def get_all_roles(self) -> List[str]:
        """Get list of all supported roles."""
        return list(self.role_taxonomy.keys())

    def analyze_role_match(
        self,
        resume_text: str,
        job_text: str
    ) -> Dict:
        """
        Full role match analysis for a candidate-job pair.

        Returns:
            {
                "candidate_role": str or None,
                "candidate_role_confidence": float,
                "job_role": str or None,
                "job_role_confidence": float,
                "role_similarity": float,
                "is_strong_match": bool,
                "is_mismatch": bool
            }
        """
        candidate_role, candidate_conf = self.detect_role(resume_text, "resume")
        job_role, job_conf = self.detect_role(job_text, "job")

        similarity = self.get_role_similarity(candidate_role, job_role)

        return {
            "candidate_role": candidate_role,
            "candidate_role_confidence": round(candidate_conf, 3),
            "job_role": job_role,
            "job_role_confidence": round(job_conf, 3),
            "role_similarity": round(similarity, 3),
            "is_strong_match": similarity >= 0.80,
            "is_mismatch": similarity < 0.30,
        }
