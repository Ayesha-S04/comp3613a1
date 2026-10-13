from __future__ import annotations

from typing import List

from sqlmodel import Session, select

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


class AdvisingRepository:
    def __init__(self, db: Session):
        self.db = db

    def seed_demo_data(self) -> None:
        student_user = self.db.exec(select(User).where(User.username == "bob")).one_or_none()
        advisor_user = self.db.exec(select(User).where(User.username == "admin")).one_or_none()

        if student_user is None or advisor_user is None:
            return

        program = self.db.exec(select(DegreeProgram).where(DegreeProgram.name == "BSc Computer Science")).one_or_none()
        if program is None:
            program = DegreeProgram(name="BSc Computer Science", total_credits_required=93)
            self.db.add(program)
            self.db.commit()
            self.db.refresh(program)
        elif program.total_credits_required != 93:
            program.total_credits_required = 93
            self.db.add(program)

        if not self.db.exec(select(StudentProfile).where(StudentProfile.user_id == student_user.id)).one_or_none():
            student_profile = StudentProfile(
                user_id=student_user.id,
                student_code="S-1001",
                first_name="Bob",
                last_name="Student",
                program_id=program.id,
                year_of_study=2,
            )
            self.db.add(student_profile)
            self.db.commit()
            self.db.refresh(student_profile)
        else:
            student_profile = self.db.exec(select(StudentProfile).where(StudentProfile.user_id == student_user.id)).one_or_none()
            if student_profile.year_of_study == 1:
                student_profile.year_of_study = 2
                self.db.add(student_profile)
                self.db.commit()

        if not self.db.exec(select(AcademicAdvisorProfile).where(AcademicAdvisorProfile.user_id == advisor_user.id)).one_or_none():
            advisor_profile = AcademicAdvisorProfile(
                user_id=advisor_user.id,
                advisor_code="A-2001",
                first_name="Admin",
                last_name="Advisor",
            )
            self.db.add(advisor_profile)
            self.db.commit()
            self.db.refresh(advisor_profile)
        else:
            advisor_profile = self.db.exec(select(AcademicAdvisorProfile).where(AcademicAdvisorProfile.user_id == advisor_user.id)).one_or_none()

        courses_by_code: dict[str, Course] = {}
        for course in self.db.exec(select(Course)).all():
            courses_by_code[course.code] = course

        catalog = {
            "CS101": ("Intro to Programming", 3, "core"),
            "CS102": ("Data Structures", 3, "core"),
            "CS201": ("Object-Oriented Design", 3, "core"),
            "ENG101": ("Academic Writing", 3, "core"),
            "MATH201": ("Calculus II", 3, "core"),
            "CS240": ("Systems and Networks", 3, "core"),
            "CS310": ("Software Design", 3, "core"),
            "CS220": ("Database Systems", 3, "core"),
            "CS230": ("Web Application Development", 3, "core"),
            "CS260": ("User Experience Design", 3, "elective"),
            "CS280": ("Introduction to Data Science", 3, "elective"),
            "CS120": ("Discrete Mathematics", 3, "core"),
            "CS210": ("Algorithms", 3, "core"),
            "CS250": ("Operating Systems", 3, "core"),
            "CS270": ("Computer Architecture", 3, "core"),
            "CS300": ("Software Engineering", 3, "core"),
            "CS320": ("Computer Networks", 3, "core"),
            "CS330": ("Database Applications", 3, "core"),
            "CS340": ("Theory of Computation", 3, "core"),
            "CS350": ("Computing Capstone I", 3, "core"),
            "CS360": ("Computing Capstone II", 3, "core"),
            "MATH220": ("Linear Algebra", 3, "core"),
            "STAT200": ("Statistics for Computing", 3, "core"),
            "CS410": ("Artificial Intelligence", 3, "elective"),
            "CS420": ("Machine Learning", 3, "elective"),
            "CS430": ("Cybersecurity", 3, "elective"),
            "CS440": ("Cloud Computing", 3, "elective"),
            "CS450": ("Mobile Application Development", 3, "elective"),
            "CS460": ("Computer Graphics", 3, "elective"),
            "CS470": ("Natural Language Processing", 3, "elective"),
            "CS480": ("Robotics", 3, "elective"),
            "CS490": ("Computer Vision", 3, "elective"),
            "CS491": ("Game Development", 3, "elective"),
            "CS492": ("Blockchain Technologies", 3, "elective"),
            "CS493": ("Bioinformatics", 3, "elective"),
            "CS494": ("Distributed Systems", 3, "elective"),
            "CS495": ("Information Retrieval", 3, "elective"),
            "CS496": ("Data Visualization", 3, "elective"),
            "CS497": ("Digital Forensics", 3, "elective"),
            "CS498": ("Human-Computer Interaction", 3, "elective"),
            "CS499": ("Topics in Computing", 3, "elective"),
            "CS401": ("Ethical Computing", 3, "elective"),
            "CS402": ("Computational Biology", 3, "elective"),
            "CS403": ("Numerical Computing", 3, "elective"),
            "CS404": ("Parallel Programming", 3, "elective"),
            "CS405": ("Computer Security", 3, "elective"),
            "CS406": ("E-Commerce Systems", 3, "elective"),
            "CS407": ("Data Mining", 3, "elective"),
            "CS408": ("Multimedia Systems", 3, "elective"),
            "CS409": ("IT Project Management", 3, "elective"),
        }

        for code, (name, credits, course_type) in catalog.items():
            course = courses_by_code.get(code)
            if course is None:
                course = Course(code=code, name=name, credits=credits, course_type=course_type)
                self.db.add(course)
                courses_by_code[code] = course
            else:
                course.name = name
                course.credits = credits
                course.course_type = course_type

        self.db.flush()
        requirements_by_course = {
            requirement.course_id: requirement
            for requirement in self.db.exec(
                select(ProgramRequirement).where(ProgramRequirement.program_id == program.id)
            ).all()
        }
        for code, (_, _, course_type) in catalog.items():
            course = courses_by_code[code]
            requirement = requirements_by_course.get(course.id)
            if requirement is None:
                self.db.add(
                    ProgramRequirement(
                        program_id=program.id,
                        course_id=course.id,
                        requirement_type=course_type,
                    )
                )
            else:
                requirement.requirement_type = course_type
        self.db.commit()

        if not self.db.exec(select(StudentCourse).where(StudentCourse.student_id == student_profile.id)).first():
            completed = [
                ("CS101", "Semester 1", "2023/2024", "A"),
                ("ENG101", "Semester 1", "2023/2024", "B"),
                ("MATH201", "Semester 2", "2023/2024", "A-"),
            ]
            for code, semester, academic_year, grade in completed:
                course = courses_by_code[code]
                self.db.add(
                    StudentCourse(
                        student_id=student_profile.id,
                        course_id=course.id,
                        semester=semester,
                        academic_year=academic_year,
                        grade=grade,
                        completion_status="completed",
                    )
                )
            self.db.commit()

        if not self.db.exec(select(SemesterPlan).where(SemesterPlan.student_id == student_profile.id)).first():
            plan_courses = [courses_by_code[code].id for code in ["CS102", "CS201", "CS240"]]
            plan = SemesterPlan(
                student_id=student_profile.id,
                advisor_id=advisor_profile.id,
                semester="Semester 2",
                academic_year="2024/2025",
                approval_status="pending",
            )
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
            for course_id in plan_courses:
                self.db.add(SemesterPlanCourse(plan_id=plan.id, course_id=course_id))
            self.db.commit()

    def get_student_profile_for_user(self, user_id: int):
        return self.db.exec(select(StudentProfile).where(StudentProfile.user_id == user_id)).one_or_none()

    def get_student_profile(self, student_id: int) -> StudentProfile | None:
        return self.db.get(StudentProfile, student_id)

    def get_advisor_profile_for_user(self, user_id: int):
        return self.db.exec(select(AcademicAdvisorProfile).where(AcademicAdvisorProfile.user_id == user_id)).one_or_none()

    def get_user_by_username(self, username: str) -> User | None:
        return self.db.exec(select(User).where(User.username == username)).one_or_none()

    def get_advisor_profile_for_user_by_username(self, username: str) -> AcademicAdvisorProfile | None:
        return self.db.exec(
            select(AcademicAdvisorProfile)
            .join(User, AcademicAdvisorProfile.user_id == User.id)
            .where(User.username == username)
        ).one_or_none()

    def get_degree_program(self, program_id: int):
        return self.db.get(DegreeProgram, program_id)

    def get_default_program(self) -> DegreeProgram | None:
        return self.db.exec(select(DegreeProgram)).first()

    def get_plans_by_status(
        self,
        approval_status: str,
        advisor_id: int | None = None,
    ) -> List[SemesterPlan]:
        statement = select(SemesterPlan).where(SemesterPlan.approval_status == approval_status)
        if advisor_id is not None:
            statement = statement.where(SemesterPlan.advisor_id == advisor_id)
        return self.db.exec(
            statement.order_by(SemesterPlan.submission_date.desc())
        ).all()

    def get_program_requirements(self, program_id: int) -> List[ProgramRequirement]:
        return self.db.exec(select(ProgramRequirement).where(ProgramRequirement.program_id == program_id)).all()

    def get_student_course_history(self, student_id: int) -> List[StudentCourse]:
        return self.db.exec(select(StudentCourse).where(StudentCourse.student_id == student_id)).all()

    def get_courses(self) -> List[Course]:
        return self.db.exec(select(Course)).all()

    def get_course(self, course_id: int) -> Course | None:
        return self.db.get(Course, course_id)

    def get_plan_for_student(self, student_id: int):
        return self.db.exec(select(SemesterPlan).where(SemesterPlan.student_id == student_id).order_by(SemesterPlan.submission_date.desc())).all()

    def create_plan(
        self,
        student_id: int,
        advisor_id: int | None,
        semester: str,
        academic_year: str,
        course_ids: list[int],
        student_comments: str | None = None,
    ) -> SemesterPlan:
        plan = SemesterPlan(
            student_id=student_id,
            advisor_id=advisor_id,
            semester=semester,
            academic_year=academic_year,
            approval_status="pending",
            student_comments=student_comments,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        for course_id in sorted(set(course_ids)):
            self.db.add(SemesterPlanCourse(plan_id=plan.id, course_id=course_id))
        self.db.commit()
        return plan

    def get_pending_plans(self) -> List[SemesterPlan]:
        return self.db.exec(select(SemesterPlan).where(SemesterPlan.approval_status == "pending").order_by(SemesterPlan.submission_date.desc())).all()

    def get_plan_courses(self, plan_id: int) -> List[SemesterPlanCourse]:
        return self.db.exec(select(SemesterPlanCourse).where(SemesterPlanCourse.plan_id == plan_id)).all()

    def get_course_prerequisites(self, course_id: int) -> List[CoursePrerequisite]:
        return self.db.exec(
            select(CoursePrerequisite).where(CoursePrerequisite.course_id == course_id)
        ).all()

    def get_plan_by_id(self, plan_id: int) -> SemesterPlan | None:
        return self.db.get(SemesterPlan, plan_id)

    def create_review(self, plan_id: int, advisor_id: int, decision: str, feedback: str | None) -> PlanReview:
        review = PlanReview(
            plan_id=plan_id,
            advisor_id=advisor_id,
            decision=decision,
            feedback=feedback,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def get_latest_plan_review(self, plan_id: int, decision: str) -> PlanReview | None:
        return self.db.exec(
            select(PlanReview)
            .where(PlanReview.plan_id == plan_id, PlanReview.decision == decision)
            .order_by(PlanReview.review_date.desc(), PlanReview.id.desc())
        ).first()

    def update_plan_status(self, plan_id: int, approval_status: str):
        plan = self.db.get(SemesterPlan, plan_id)
        if plan is None:
            raise ValueError("Plan not found")
        plan.approval_status = approval_status
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def create_student_profile(self, user_id: int, first_name: str, last_name: str, program_id: int | None) -> StudentProfile:
        profile = StudentProfile(
            user_id=user_id,
            student_code=f"S-{user_id:04d}",
            first_name=first_name,
            last_name=last_name,
            program_id=program_id,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def create_advisor_profile(self, user_id: int, first_name: str, last_name: str) -> AcademicAdvisorProfile:
        profile = AcademicAdvisorProfile(
            user_id=user_id,
            advisor_code=f"A-{user_id:04d}",
            first_name=first_name,
            last_name=last_name,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
