"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.advising import (
    AcademicAdvisorProfile,
    Course,
    CoursePrerequisite,
    DegreeProgram,
    PlanReview,
    ProgramRequirement,
    SemesterPlan,
    SemesterPlanCourse,
    StudentCourse,
    StudentProfile,
)
from app.models.user import User

__all__ = [
    "User",
    "DegreeProgram",
    "StudentProfile",
    "AcademicAdvisorProfile",
    "Course",
    "ProgramRequirement",
    "CoursePrerequisite",
    "StudentCourse",
    "SemesterPlan",
    "SemesterPlanCourse",
    "PlanReview",
]
