"""
Comprehensive skills database used for skill extraction from resumes and job descriptions.
Organised by domain for maintainability.
"""

PROGRAMMING_LANGUAGES = [
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "haskell", "elixir", "clojure", "lua", "dart", "groovy", "objective-c",
    "assembly", "fortran", "cobol", "vba", "sas",
]

WEB_FRONTEND = [
    "html", "css", "sass", "scss", "less", "react", "react.js", "angular",
    "vue", "vue.js", "svelte", "next.js", "gatsby", "nuxt.js", "jquery",
    "bootstrap", "tailwind", "tailwindcss", "material ui", "chakra ui",
    "webpack", "vite", "babel", "redux", "mobx", "graphql", "websocket",
]

WEB_BACKEND = [
    "node.js", "express", "express.js", "django", "flask", "fastapi",
    "spring", "spring boot", "asp.net", "rails", "ruby on rails", "laravel",
    "nestjs", "hapi", "koa", "gin", "fiber", "actix", "rocket", "phoenix",
    "rest api", "restful", "microservices", "grpc", "soap",
]

DATABASES = [
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "sqlite",
    "oracle", "sql server", "mssql", "cassandra", "dynamodb", "elasticsearch",
    "neo4j", "couchdb", "influxdb", "clickhouse", "mariadb", "firebase",
    "supabase", "pinecone", "weaviate", "chroma", "qdrant",
]

CLOUD_DEVOPS = [
    "aws", "amazon web services", "azure", "microsoft azure", "gcp",
    "google cloud", "docker", "kubernetes", "k8s", "terraform", "ansible",
    "jenkins", "circleci", "github actions", "gitlab ci", "travis ci",
    "helm", "istio", "prometheus", "grafana", "datadog", "splunk",
    "nginx", "apache", "linux", "unix", "bash", "shell scripting",
    "powershell", "vagrant", "packer", "chef", "puppet", "serverless",
    "lambda", "cloudformation", "pulumi", "argocd", "flux",
]

ML_AI = [
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning", "neural networks",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "xgboost", "lightgbm", "catboost", "pandas", "numpy", "scipy",
    "matplotlib", "seaborn", "plotly", "nltk", "spacy", "hugging face",
    "transformers", "bert", "gpt", "llm", "rag", "langchain",
    "opencv", "pillow", "yolo", "stable diffusion", "openai",
    "feature engineering", "model deployment", "mlops", "mlflow",
    "kubeflow", "sagemaker", "vertex ai", "azure ml",
    "data augmentation", "transfer learning", "fine-tuning",
    "time series", "forecasting", "anomaly detection", "clustering",
    "classification", "regression", "recommendation system",
]

DATA_ENGINEERING = [
    "apache spark", "spark", "hadoop", "kafka", "apache kafka",
    "airflow", "apache airflow", "dbt", "databricks", "snowflake",
    "bigquery", "redshift", "data warehouse", "etl", "elt",
    "data pipeline", "data lake", "delta lake", "hive", "pig",
    "flink", "storm", "nifi", "talend", "informatica",
    "power bi", "tableau", "looker", "metabase", "superset", "qlik",
]

VERSION_CONTROL = [
    "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
    "code review", "pull request", "branching strategy",
]

METHODOLOGIES = [
    "agile", "scrum", "kanban", "lean", "waterfall", "devops",
    "ci/cd", "tdd", "bdd", "pair programming", "code review",
    "design patterns", "solid principles", "oop", "functional programming",
    "microservices architecture", "event-driven architecture",
    "domain-driven design", "ddd", "clean architecture",
]

SECURITY = [
    "cybersecurity", "penetration testing", "owasp", "ssl", "tls",
    "oauth", "jwt", "authentication", "authorization", "encryption",
    "firewall", "vpn", "siem", "soc", "vulnerability assessment",
    "network security", "ethical hacking", "burp suite", "nmap",
]

MOBILE = [
    "android", "ios", "react native", "flutter", "xamarin",
    "ionic", "cordova", "mobile development", "swift", "kotlin",
]

TOOLS_GENERAL = [
    "jira", "confluence", "slack", "trello", "notion", "asana",
    "postman", "swagger", "insomnia", "figma", "adobe xd",
    "vs code", "intellij", "pycharm", "eclipse", "visual studio",
    "excel", "microsoft office", "google workspace",
    "linux administration", "system design", "api design",
    "data structures", "algorithms", "object-oriented programming",
    "unit testing", "integration testing", "selenium", "cypress",
    "jest", "pytest", "junit", "mocha", "chai",
]

CERTIFICATIONS = [
    "aws certified", "google cloud certified", "microsoft certified",
    "cisco ccna", "cisco ccnp", "pmp", "prince2", "scrum master",
    "certified scrum master", "csm", "comptia security+", "comptia a+",
    "certified ethical hacker", "ceh", "cissp", "cisa", "azure certified",
    "gcp certified", "terraform certified", "kubernetes certified", "ckad", "cka",
    "oracle certified", "salesforce certified", "servicenow certified",
]

SOFT_SKILLS = [
    "leadership", "communication", "teamwork", "problem solving",
    "critical thinking", "project management", "time management",
    "presentation skills", "mentoring", "coaching",
]

# Merged flat list used for skill extraction
ALL_SKILLS: list[str] = list({
    skill.lower() for skill in (
        PROGRAMMING_LANGUAGES + WEB_FRONTEND + WEB_BACKEND + DATABASES
        + CLOUD_DEVOPS + ML_AI + DATA_ENGINEERING + VERSION_CONTROL
        + METHODOLOGIES + SECURITY + MOBILE + TOOLS_GENERAL + CERTIFICATIONS
    )
})

EDUCATION_KEYWORDS = [
    "b.tech", "m.tech", "b.e", "m.e", "b.sc", "m.sc", "phd", "ph.d",
    "mba", "bachelor", "master", "doctorate", "associate",
    "computer science", "information technology", "software engineering",
    "electrical engineering", "electronics", "mathematics", "statistics",
    "data science", "artificial intelligence", "machine learning",
    "business administration", "information systems",
    "university", "college", "institute", "school", "academy",
]

CERTIFICATION_KEYWORDS = [
    "certified", "certification", "certificate", "aws", "google cloud",
    "microsoft", "azure", "cisco", "oracle", "comptia", "pmp", "scrum",
    "coursera", "udemy", "edx", "linkedin learning", "pluralsight",
    "credential", "badge", "license",
]

EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
    r"experience\s+of\s+(\d+)\+?\s*years?",
    r"(\d+)\s*-\s*(\d+)\s*years?",
    r"over\s+(\d+)\s+years?",
]
