"""
Skill Ontology for Domain-Aware Skill Matching

Replaces plain keyword matching with structured domains.
Ensures Cloud skills don't score high for Data Science jobs.
"""

from typing import Dict, List, Set, Tuple
from collections import defaultdict
import re


# Skill domains with normalized skill names
SKILL_DOMAINS = {
    "Cloud": {
        "aws", "azure", "gcp", "google cloud", "cloud computing",
        "ec2", "s3", "lambda", "cloudformation", "vpc",
        "azure devops", "azure functions", "compute engine",
        "cloud architecture", "cloud security", "iam",
        "cloudwatch", "cloud monitoring", "cloud storage",
        "elastic beanstalk", "lightsail"
    },
    "DevOps": {
        "docker", "kubernetes", "k8s", "jenkins", "ci/cd",
        "terraform", "ansible", "puppet", "chef", "vagrant",
        "gitlab ci", "github actions", "circleci", "travis ci",
        "helm", "argocd", "prometheus", "grafana", "elk stack",
        "linux", "bash", "shell scripting", "automation",
        "infrastructure as code", "gitops", "monitoring"
    },
    "Backend": {
        "python", "java", "node.js", "nodejs", "go", "golang",
        "c#", "ruby", "php", "rust", "scala", "kotlin",
        "fastapi", "django", "flask", "spring", "spring boot",
        "express", "nest.js", "ruby on rails", "laravel",
        "rest api", "graphql", "microservices", "api design",
        "postgresql", "mysql", "mongodb", "redis", "cassandra",
        "sql", "nosql", "database design", "orm", "sqlalchemy",
        "hibernate", "prisma"
    },
    "Frontend": {
        "react", "angular", "vue", "vue.js", "svelte",
        "javascript", "typescript", "html", "css", "sass",
        "next.js", "nuxt.js", "gatsby", "webpack", "vite",
        "tailwind", "bootstrap", "material-ui", "mui",
        "redux", "vuex", "state management", "responsive design",
        "ui/ux", "accessibility", "web components", "jquery"
    },
    "Mobile": {
        "swift", "kotlin", "react native", "flutter", "xamarin",
        "ios", "android", "mobile development", "xcode",
        "android studio", "firebase", "core data", "realm",
        "jetpack compose", "swiftui"
    },
    "Data Science": {
        "python", "r", "statistics", "statistical analysis",
        "pandas", "numpy", "scipy", "matplotlib", "seaborn",
        "plotly", "jupyter", "data analysis", "exploratory data analysis",
        "hypothesis testing", "a/b testing", "regression",
        "classification", "clustering", "time series",
        "data visualization", "tableau", "power bi",
        "excel", "sql", "data mining"
    },
    "Machine Learning": {
        "machine learning", "ml", "deep learning", "neural networks",
        "tensorflow", "pytorch", "keras", "scikit-learn",
        "xgboost", "lightgbm", "catboost", "random forest",
        "gradient boosting", "svm", "decision trees",
        "nlp", "natural language processing", "computer vision",
        "cnn", "rnn", "lstm", "transformer", "bert", "gpt",
        "model training", "feature engineering", "hyperparameter tuning",
        "mlflow", "mlops", "model deployment", "tensorflow serving"
    },
    "AI": {
        "artificial intelligence", "ai", "generative ai",
        "llm", "large language models", "openai", "langchain",
        "prompt engineering", "fine-tuning", "rag",
        "retrieval augmented generation", "vector database",
        "embeddings", "semantic search", "chatbot", "conversational ai"
    },
    "Data Engineering": {
        "spark", "apache spark", "pyspark", "kafka", "airflow",
        "hadoop", "hive", "presto", "flink", "storm",
        "snowflake", "databricks", "bigquery", "redshift",
        "etl", "data pipeline", "data warehouse", "data lake",
        "dbt", "data modeling", "stream processing",
        "batch processing", "data orchestration"
    },
    "QA": {
        "selenium", "junit", "pytest", "testng", "jest",
        "mocha", "cypress", "playwright", "puppeteer",
        "test automation", "unit testing", "integration testing",
        "e2e testing", "regression testing", "load testing",
        "performance testing", "api testing", "postman",
        "jmeter", "test-driven development", "tdd", "bdd",
        "cucumber", "quality assurance", "bug tracking", "jira"
    },
    "Security": {
        "cybersecurity", "information security", "appsec",
        "penetration testing", "ethical hacking", "vulnerability assessment",
        "siem", "security operations", "threat detection",
        "iam", "identity and access management", "oauth", "saml",
        "encryption", "ssl", "tls", "firewall", "ids", "ips",
        "owasp", "security scanning", "burp suite", "nessus",
        "wireshark", "metasploit", "kali linux"
    },
    "Database": {
        "postgresql", "mysql", "oracle", "sql server", "mariadb",
        "mongodb", "cassandra", "redis", "dynamodb", "couchbase",
        "neo4j", "elasticsearch", "sql", "nosql", "database administration",
        "database design", "query optimization", "indexing",
        "replication", "sharding", "backup and recovery"
    },
    "Product Management": {
        "product strategy", "roadmap", "stakeholder management",
        "agile", "scrum", "kanban", "product lifecycle",
        "user stories", "backlog management", "jira", "confluence",
        "product analytics", "a/b testing", "market research",
        "competitive analysis", "product-market fit", "mvp"
    },
}


# Skill synonyms and variations
SKILL_SYNONYMS = {
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "tf": "tensorflow",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "db": "database",
    "sql server": "microsoft sql server",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "node": "node.js",
    "react.js": "react",
    "vue.js": "vue",
    "next": "next.js",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
}


class SkillOntology:
    """Domain-aware skill matching and analysis."""

    def __init__(self):
        self.skill_domains = SKILL_DOMAINS
        self.skill_synonyms = SKILL_SYNONYMS

        # Build reverse index: skill -> domain
        self.skill_to_domain = {}
        for domain, skills in self.skill_domains.items():
            for skill in skills:
                self.skill_to_domain[skill.lower()] = domain

    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name (lowercase, handle synonyms)."""
        skill_lower = skill.lower().strip()
        return self.skill_synonyms.get(skill_lower, skill_lower)

    def normalize_skill_list(self, skills: List[str]) -> Set[str]:
        """Normalize a list of skills."""
        return {self.normalize_skill(s) for s in skills if s}

    def get_skill_domain(self, skill: str) -> str:
        """Get domain for a skill (e.g., 'docker' -> 'DevOps')."""
        normalized = self.normalize_skill(skill)
        return self.skill_to_domain.get(normalized, "Other")

    def compute_domain_distribution(self, skills: List[str]) -> Dict[str, int]:
        """
        Compute domain distribution for a skill list.

        Returns:
            {"Cloud": 5, "Backend": 3, "DevOps": 2, ...}
        """
        distribution = defaultdict(int)
        for skill in skills:
            domain = self.get_skill_domain(skill)
            distribution[domain] += 1
        return dict(distribution)

    def compute_domain_match(
        self,
        candidate_skills: List[str],
        job_required_skills: List[str],
        job_preferred_skills: List[str] = None
    ) -> Dict:
        """
        Compute domain-level match between candidate and job.

        This prevents Cloud Engineers scoring high for Data Science jobs.

        Returns:
            {
                "candidate_domains": {"Cloud": 5, "DevOps": 3},
                "job_required_domains": {"Data Science": 4, "Machine Learning": 3},
                "domain_overlap": {"Backend": 2},
                "domain_match_score": 0.45,  # [0, 1]
                "is_domain_mismatch": False
            }
        """
        if job_preferred_skills is None:
            job_preferred_skills = []

        candidate_domains = self.compute_domain_distribution(candidate_skills)
        required_domains = self.compute_domain_distribution(job_required_skills)
        preferred_domains = self.compute_domain_distribution(job_preferred_skills)

        # Merge job domains (required + preferred)
        job_domains = defaultdict(int)
        for domain, count in required_domains.items():
            job_domains[domain] += count * 2  # Weight required higher
        for domain, count in preferred_domains.items():
            job_domains[domain] += count

        # Compute overlap
        overlap = {}
        for domain in set(candidate_domains.keys()) & set(job_domains.keys()):
            overlap[domain] = min(candidate_domains[domain], job_domains[domain])

        # Compute match score
        if not job_domains:
            domain_match_score = 0.5  # Neutral if no job skills
        else:
            overlap_weight = sum(overlap.values())
            job_weight = sum(job_domains.values())
            domain_match_score = overlap_weight / job_weight if job_weight > 0 else 0.0

        # Detect domain mismatch
        # If candidate's top domain is completely absent from job domains
        is_mismatch = False
        if candidate_domains and job_domains:
            top_candidate_domain = max(candidate_domains.items(), key=lambda x: x[1])[0]
            if top_candidate_domain not in job_domains:
                is_mismatch = True

        return {
            "candidate_domains": dict(candidate_domains),
            "job_required_domains": dict(required_domains),
            "job_preferred_domains": dict(preferred_domains),
            "domain_overlap": overlap,
            "domain_match_score": round(domain_match_score, 3),
            "is_domain_mismatch": is_mismatch,
        }

    def compute_skill_match(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        preferred_skills: List[str] = None
    ) -> Dict:
        """
        Compute detailed skill match with domain awareness.

        Returns:
            {
                "required_match_count": 3,
                "required_match_ratio": 0.75,
                "preferred_match_count": 2,
                "preferred_match_ratio": 0.40,
                "matched_skills": ["python", "tensorflow"],
                "missing_required": ["pytorch"],
                "missing_preferred": ["mlflow", "docker"],
                "extra_skills": ["aws", "kubernetes"],
                "technical_depth": 8
            }
        """
        if preferred_skills is None:
            preferred_skills = []

        candidate_normalized = self.normalize_skill_list(candidate_skills)
        required_normalized = self.normalize_skill_list(required_skills)
        preferred_normalized = self.normalize_skill_list(preferred_skills)

        # Required skill match
        matched_required = candidate_normalized & required_normalized
        missing_required = required_normalized - candidate_normalized
        required_match_ratio = (
            len(matched_required) / len(required_normalized)
            if required_normalized else 1.0
        )

        # Preferred skill match
        matched_preferred = candidate_normalized & preferred_normalized
        missing_preferred = preferred_normalized - candidate_normalized
        preferred_match_ratio = (
            len(matched_preferred) / len(preferred_normalized)
            if preferred_normalized else 0.0
        )

        # All matched skills
        all_job_skills = required_normalized | preferred_normalized
        matched_skills = candidate_normalized & all_job_skills
        extra_skills = candidate_normalized - all_job_skills

        # Technical depth (total unique skills)
        technical_depth = len(candidate_normalized)

        return {
            "required_match_count": len(matched_required),
            "required_match_ratio": round(required_match_ratio, 3),
            "preferred_match_count": len(matched_preferred),
            "preferred_match_ratio": round(preferred_match_ratio, 3),
            "matched_skills": sorted(matched_skills),
            "missing_required": sorted(missing_required),
            "missing_preferred": sorted(missing_preferred),
            "extra_skills": sorted(extra_skills),
            "technical_depth": technical_depth,
        }

    def compute_technical_breadth(self, skills: List[str]) -> float:
        """
        Compute how many distinct domains a candidate has experience in.

        Returns:
            Score [0, 1] — 0.0 = single domain, 1.0 = many domains
        """
        domains = set(self.get_skill_domain(s) for s in skills)
        domains.discard("Other")

        if not domains:
            return 0.0

        # Normalize by max realistic domain count (5-6 domains is very broad)
        breadth = min(len(domains) / 6.0, 1.0)
        return round(breadth, 3)

    def get_all_domains(self) -> List[str]:
        """Get list of all skill domains."""
        return list(self.skill_domains.keys())
