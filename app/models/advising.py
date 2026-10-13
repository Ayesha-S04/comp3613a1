from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class DegreeProgram(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    total_credits_required: int = 0


class StudentProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    student_code: str = Field(unique=True, index=True)
    first_name: str
    last_name: str
    program_id: Optional[int] = Field(default=None, foreign_key="degreeprogram.id")
    year_of_study: int = 1


class AcademicAdvisorProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    advisor_code: str = Field(unique=True, index=True)
    first_name: str
    last_name: str


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    credits: int = 3
    course_type: str = "core"


class ProgramRequirement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    program_id: int = Field(foreign_key="degreeprogram.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    requirement_type: str = "core"


class CoursePrerequisite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    required_course_id: int = Field(foreign_key="course.id", index=True)


class StudentCourse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="studentprofile.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    semester: str
    academic_year: str
    grade: Optional[str] = None
    completion_status: str = "completed"


class SemesterPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="studentprofile.id", index=True)
    advisor_id: Optional[int] = Field(default=None, foreign_key="academicadvisorprofile.id")
    semester: str
    academic_year: str
    submission_date: datetime = Field(default_factory=datetime.utcnow)
    approval_status: str = "pending"
    student_comments: Optional[str] = None


class SemesterPlanCourse(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("plan_id", "course_id", name="uq_plan_course"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="semesterplan.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)

class PlanReview(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="semesterplan.id", index=True)
    advisor_id: int = Field(foreign_key="academicadvisorprofile.id", index=True)
    decision: str
    feedback: Optional[str] = None
    review_date: datetime = Field(default_factory=datetime.utcnow)
