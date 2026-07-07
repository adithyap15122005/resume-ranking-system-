"""
Sample data generator.

Creates 20 realistic synthetic resumes and 5 job descriptions for
testing when no Kaggle dataset is available.

Run standalone:
    python -m data.sample_generator

Or call programmatically:
    from data.sample_generator import generate_all
    generate_all(db_session)
"""
import logging
import random
import textwrap
from typing import List

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.job import JobDescription
from backend.models.resume import Resume
from backend.utils.resume_parser import ResumeParser
from backend.utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)

# ── Templates ─────────────────────────────────────────────────────────────────

_FIRST_NAMES = [
    "Arjun", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Rohan", "Kavya",
    "Aditya", "Divya", "Karthik", "Meera", "Siddharth", "Pooja", "Nikhil",
    "Shreya", "Suresh", "Lakshmi", "Deepak", "Nisha",
]
_LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Mehta", "Reddy", "Iyer",
    "Bose", "Nair", "Joshi", "Verma", "Das", "Chopra", "Malhotra",
]
_UNIVERSITIES = [
    "IIT Delhi", "NIT Trichy", "BITS Pilani", "IIT Bombay", "VIT University",
    "Anna University", "JNTU Hyderabad", "Manipal Institute of Technology",
    "SRM Institute", "Amrita School of Engineering",
]
_COMPANIES = [
    "Infosys", "TCS", "Wipro", "HCL Technologies", "Accenture", "Cognizant",
    "Tech Mahindra", "Capgemini", "IBM India", "Oracle India",
    "Flipkart", "Paytm", "Swiggy", "Zomato", "Razorpay",
]

PROFILES = [
    {
        "role": "Data Scientist",
        "skills": [
            "Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
            "Scikit-learn", "Pandas", "NumPy", "SQL", "Tableau", "NLP", "BERT",
            "Feature Engineering", "Data Visualization", "AWS",
        ],
        "tools": ["Jupyter", "VS Code", "Git", "Docker", "MLflow"],
        "certs": ["AWS Certified Machine Learning Specialty", "Google Data Analytics"],
        "projects": [
            "Fraud Detection System using XGBoost achieving 97% AUC",
            "Customer Churn Prediction with LSTM — reduced churn by 23%",
            "Sentiment Analysis pipeline using BERT for e-commerce reviews",
        ],
    },
    {
        "role": "Software Engineer",
        "skills": [
            "Java", "Spring Boot", "Python", "React", "Node.js", "MySQL",
            "PostgreSQL", "Docker", "Kubernetes", "REST API", "Microservices",
            "Git", "Agile", "AWS", "CI/CD",
        ],
        "tools": ["IntelliJ", "Postman", "Jenkins", "Jira"],
        "certs": ["Oracle Certified Java Programmer", "AWS Developer Associate"],
        "projects": [
            "Built microservices-based e-commerce platform serving 50k daily users",
            "Developed real-time inventory management system with WebSocket",
            "Migrated monolith to Kubernetes, reducing deployment time by 60%",
        ],
    },
    {
        "role": "DevOps Engineer",
        "skills": [
            "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins",
            "GitHub Actions", "AWS", "Azure", "Linux", "Bash", "Python",
            "Prometheus", "Grafana", "Nginx", "CI/CD",
        ],
        "tools": ["Helm", "ArgoCD", "Datadog", "Splunk"],
        "certs": ["CKA — Certified Kubernetes Administrator", "AWS Solutions Architect"],
        "projects": [
            "Automated infrastructure provisioning with Terraform — 70% faster deployments",
            "Set up multi-region Kubernetes cluster on AWS EKS for 99.99% uptime",
            "Built end-to-end CI/CD pipeline reducing release cycle from 2 weeks to 1 day",
        ],
    },
    {
        "role": "ML Engineer",
        "skills": [
            "Python", "TensorFlow", "PyTorch", "MLflow", "Kubeflow",
            "Docker", "Kubernetes", "AWS SageMaker", "Spark", "SQL",
            "FastAPI", "Redis", "Kafka", "Model Deployment", "Deep Learning",
        ],
        "tools": ["DVC", "Weights & Biases", "Airflow", "Databricks"],
        "certs": ["AWS Certified Machine Learning", "Google Professional ML Engineer"],
        "projects": [
            "Deployed real-time recommendation engine processing 1M requests/day",
            "Built AutoML pipeline reducing model training time by 40%",
            "Developed NLP model for document classification with 94% accuracy",
        ],
    },
    {
        "role": "Frontend Developer",
        "skills": [
            "React", "TypeScript", "JavaScript", "HTML", "CSS", "Next.js",
            "Redux", "GraphQL", "Webpack", "Jest", "Tailwind CSS",
            "Node.js", "Git", "Figma", "REST API",
        ],
        "tools": ["VS Code", "Chrome DevTools", "Storybook"],
        "certs": ["Meta Front-End Developer Certificate"],
        "projects": [
            "Built SPA for EdTech platform with 200k MAU using React + Redux",
            "Developed component library used across 5 product teams",
            "Implemented SSR with Next.js improving LCP by 45%",
        ],
    },
]


def _make_resume(name: str, profile: dict, years: float) -> str:
    skills_str = " | ".join(profile["skills"])
    tools_str = " | ".join(profile["tools"])
    proj_str = "\n  - ".join(profile["projects"])
    cert_str = "\n  - ".join(profile["certs"])
    uni = random.choice(_UNIVERSITIES)
    company1 = random.choice(_COMPANIES)
    company2 = random.choice([c for c in _COMPANIES if c != company1])
    email = f"{name.lower().replace(' ', '.')}@email.com"
    phone = f"+91 9{random.randint(100000000, 999999999)}"

    return textwrap.dedent(f"""
    {name}
    {email} | {phone} | LinkedIn: linkedin.com/in/{name.lower().replace(' ', '')}

    OBJECTIVE
    Experienced {profile['role']} with {years} years of hands-on industry experience.
    Passionate about building scalable, production-grade systems and solving complex problems.

    SKILLS
    {skills_str}

    TOOLS & TECHNOLOGIES
    {tools_str}

    EXPERIENCE

    {profile['role']} — {company1}
    January 2022 – Present
    - Designed and implemented end-to-end ML pipelines handling 10M+ records daily
    - Collaborated with cross-functional teams using Agile/Scrum methodology
    - Reduced model inference latency by 35% through optimization

    Junior {profile['role']} — {company2}
    July 2019 – December 2021
    - Developed and maintained production applications serving 100k+ users
    - Participated in code reviews and mentored junior developers
    - Automated testing reducing bug rate by 28%

    EDUCATION
    B.Tech in Computer Science and Engineering
    {uni}
    CGPA: {round(random.uniform(7.5, 9.8), 1)} | Graduated 2019

    PROJECTS
    - {proj_str}

    CERTIFICATIONS
    - {cert_str}

    LANGUAGES
    English (Fluent) | Hindi (Native)
    """).strip()


# ── Job descriptions ──────────────────────────────────────────────────────────

JOB_DESCRIPTIONS = [
    {
        "title": "Senior Data Scientist",
        "text": textwrap.dedent("""
        We are looking for a Senior Data Scientist to join our AI/ML team.

        Requirements:
        - 3+ years of experience in machine learning and data science
        - Proficiency in Python, TensorFlow or PyTorch, Scikit-learn
        - Strong knowledge of NLP, Deep Learning, Feature Engineering
        - Experience with SQL and NoSQL databases (MySQL, PostgreSQL, MongoDB)
        - Hands-on experience with AWS SageMaker or similar cloud ML platforms
        - Familiarity with MLflow, Kubeflow or other MLOps tools
        - Experience deploying models to production using FastAPI or Flask
        - Strong understanding of statistics and probability

        Nice to have:
        - BERT, Transformers, LLMs experience
        - Apache Spark for large-scale data processing
        - Tableau or Power BI for visualisation

        You will:
        - Design and implement end-to-end ML pipelines
        - Collaborate with data engineers and product teams
        - Present insights to stakeholders
        """).strip(),
    },
    {
        "title": "Full Stack Software Engineer",
        "text": textwrap.dedent("""
        Join our engineering team as a Full Stack Software Engineer.

        Requirements:
        - 2+ years of experience in full-stack development
        - Strong proficiency in React, TypeScript, and Node.js
        - Backend experience with Python (Django/FastAPI) or Java (Spring Boot)
        - Database experience: PostgreSQL, MySQL, MongoDB, Redis
        - RESTful API design and GraphQL
        - Docker, Kubernetes, CI/CD pipelines
        - Git workflow, code review, Agile/Scrum

        Nice to have:
        - Microservices architecture
        - AWS or Azure cloud services
        - Performance optimisation experience

        You will:
        - Develop and maintain scalable web applications
        - Work closely with product and design teams
        - Participate in architecture decisions
        """).strip(),
    },
    {
        "title": "DevOps Engineer",
        "text": textwrap.dedent("""
        We are hiring a DevOps Engineer to strengthen our infrastructure team.

        Requirements:
        - 2+ years of experience in DevOps/SRE
        - Expert knowledge of Docker and Kubernetes
        - Infrastructure as Code: Terraform, Ansible
        - CI/CD pipelines: Jenkins, GitHub Actions, or GitLab CI
        - Cloud platforms: AWS, Azure, or GCP
        - Linux system administration
        - Monitoring: Prometheus, Grafana, Datadog

        Nice to have:
        - CKA or AWS certifications
        - Service mesh (Istio)
        - GitOps with ArgoCD or Flux

        You will:
        - Manage and scale cloud infrastructure
        - Implement and maintain CI/CD pipelines
        - Drive reliability and performance improvements
        """).strip(),
    },
    {
        "title": "Machine Learning Engineer",
        "text": textwrap.dedent("""
        Seeking a Machine Learning Engineer to productionise our ML systems.

        Requirements:
        - 2+ years in ML engineering or data science with deployment experience
        - Python, TensorFlow or PyTorch
        - MLOps: MLflow, Kubeflow, DVC, or Weights & Biases
        - Model serving: FastAPI, TorchServe, TF Serving
        - Docker, Kubernetes
        - Apache Spark or Kafka for data pipelines
        - AWS SageMaker or Vertex AI

        Nice to have:
        - Databricks, Snowflake
        - Real-time inference at scale
        - A/B testing frameworks

        You will:
        - Bridge the gap between research and production
        - Build scalable model serving infrastructure
        - Collaborate with data scientists and engineers
        """).strip(),
    },
    {
        "title": "Frontend Developer",
        "text": textwrap.dedent("""
        We need a talented Frontend Developer to build our next-generation UI.

        Requirements:
        - 2+ years of experience in frontend development
        - Expert knowledge of React, TypeScript, JavaScript (ES6+)
        - CSS frameworks: Tailwind CSS, Bootstrap
        - State management: Redux, Zustand, or MobX
        - Testing: Jest, React Testing Library, Cypress
        - Version control: Git, GitHub
        - Responsive design and cross-browser compatibility

        Nice to have:
        - Next.js for SSR/SSG
        - GraphQL
        - Figma or Adobe XD for design collaboration

        You will:
        - Build fast, accessible, and beautiful user interfaces
        - Work closely with designers and backend engineers
        - Champion frontend best practices
        """).strip(),
    },
]


# ── Generator function ────────────────────────────────────────────────────────

def generate_resumes(n_per_profile: int = 4) -> List[str]:
    """Generate synthetic resume texts — returns list of raw text strings."""
    texts: List[str] = []
    names_used: set[str] = set()

    for profile in PROFILES:
        for _ in range(n_per_profile):
            first = random.choice(_FIRST_NAMES)
            last = random.choice(_LAST_NAMES)
            name = f"{first} {last}"
            while name in names_used:
                first = random.choice(_FIRST_NAMES)
                last = random.choice(_LAST_NAMES)
                name = f"{first} {last}"
            names_used.add(name)

            years = round(random.uniform(1.5, 8.0), 1)
            # Shuffle skills so each resume is unique
            profile_copy = dict(profile)
            skills = list(profile["skills"])
            random.shuffle(skills)
            profile_copy["skills"] = skills[: random.randint(8, len(skills))]

            texts.append(_make_resume(name, profile_copy, years))

    return texts


def generate_all(db: Session, force: bool = False) -> dict:
    """
    Insert sample resumes and job descriptions into the database.
    If force=False, skips insertion when data already exists.
    """
    from backend.utils.resume_parser import ResumeParser
    from backend.utils.text_cleaner import TextCleaner
    import hashlib

    parser = ResumeParser()
    cleaner = TextCleaner()

    existing_resumes = db.query(Resume).count()
    existing_jobs = db.query(JobDescription).count()

    if existing_resumes > 0 and not force:
        logger.info("Sample data already exists (%d resumes). Skipping.", existing_resumes)
        return {"resumes": existing_resumes, "jobs": existing_jobs}

    resume_texts = generate_resumes(n_per_profile=4)
    inserted_resumes = 0

    for i, text in enumerate(resume_texts):
        file_hash = hashlib.sha256(text.encode()).hexdigest()
        if db.query(Resume).filter(Resume.file_hash == file_hash).first():
            continue
        parsed = parser.parse_text(text, f"sample_resume_{i+1}.txt")
        cleaned = cleaner.clean(text)
        resume = Resume(
            filename=f"sample_resume_{i+1}.txt",
            filepath="",
            file_hash=file_hash,
            candidate_name=parsed.get("candidate_name"),
            email=parsed.get("email"),
            phone=parsed.get("phone"),
            skills=parsed.get("skills", []),
            education=parsed.get("education", []),
            experience=parsed.get("experience"),
            projects=parsed.get("projects", []),
            certifications=parsed.get("certifications", []),
            languages=parsed.get("languages", []),
            tools=parsed.get("tools", []),
            raw_text=text,
            cleaned_text=cleaned,
            experience_years=parsed.get("experience_years", 0.0),
            completeness_score=parsed.get("completeness_score", 0.0),
        )
        db.add(resume)
        inserted_resumes += 1

    inserted_jobs = 0
    for jd in JOB_DESCRIPTIONS:
        if db.query(JobDescription).filter(JobDescription.title == jd["title"]).first():
            continue
        parsed_jd = parser.parse_text(jd["text"])
        cleaned_jd = cleaner.clean(jd["text"])
        job = JobDescription(
            title=jd["title"],
            raw_text=jd["text"],
            cleaned_text=cleaned_jd,
            required_skills=parsed_jd.get("skills", []),
        )
        db.add(job)
        inserted_jobs += 1

    db.commit()
    logger.info(
        "Sample data generated: %d resumes, %d job descriptions.",
        inserted_resumes,
        inserted_jobs,
    )
    return {"resumes": inserted_resumes, "jobs": inserted_jobs}


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, str(settings.BASE_DIR))

    from backend.database import SessionLocal, init_db
    from backend.config import setup_logging
    setup_logging()

    init_db()
    db = SessionLocal()
    try:
        result = generate_all(db, force=True)
        print(f"Generated: {result}")
    finally:
        db.close()
