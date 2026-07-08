"""ORM models package — import all so they register with SQLAlchemy Base."""
from backend.models.organization import Organization
from backend.models.user import User
from backend.models.resume import Resume
from backend.models.job import JobDescription
from backend.models.ranking import RankingResult
from backend.models.notification import Notification
from backend.models.ml_model import MLModel
from backend.models.training_dataset import TrainingDataset
from backend.models.training_experiment import TrainingExperiment
from backend.models.hiring_outcome import HiringOutcome

__all__ = [
    "Organization",
    "User",
    "Resume",
    "JobDescription",
    "RankingResult",
    "Notification",
    "MLModel",
    "TrainingDataset",
    "TrainingExperiment",
    "HiringOutcome",
]
