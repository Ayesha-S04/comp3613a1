from __future__ import annotations

from typing import Any

from app.repositories.advising import AdvisingRepository


class AdvisingService:
    def __init__(self, repo: AdvisingRepository):
        self.repo = repo

    def ensure_demo_sections(self) -> None:
        self.repo.seed_demo_data()

    def get_student_dashboard(self, user_id: int) -> dict[str, Any]:
        self.repo.seed_demo_data()
        student_profile = self.repo.get_student_profile_for_user(user_id)
        if student_profile is None:
            program = self.repo.get_default_program()
            student_profile = self.repo.create_student_profile(user_id, "Student", "User", program.id if program else None)

        program = self.repo.get_degree_program(student_profile.program_id) if student_profile.program_id else None
        course_history = self.repo.get_student_course_history(student_profile.id)
        courses = {course.id: course for course in self.repo.get_courses()}

        completed_credits = sum(
            courses[entry.course_id].credits
            for entry in course_history
            if entry.completion_status == "completed" and entry.course_id in courses
        )
        total_credits = program.total_credits_required if program else 0
        completed_count = len([entry for entry in course_history if entry.completion_status == "completed"])
        all_plans = self.repo.get_plan_for_student(student_profile.id)
        remaining_credits = max(total_credits - completed_credits, 0)
        progress_percent = round(completed_credits / total_credits * 100) if total_credits else 0
        program_requirements = self.repo.get_program_requirements(program.id) if program else []
        course_type_by_id = {
            requirement.course_id: requirement.requirement_type
            for requirement in program_requirements
        }
        core_courses = [
            course
            for course in courses.values()
            if course.id in course_type_by_id and course_type_by_id[course.id] == "core"
        ]
        elective_courses = [
            course
            for course in courses.values()
            if course.id in course_type_by_id and course_type_by_id[course.id] == "elective"
        ]
        core_credits_required = sum(course.credits for course in core_courses)

        return {
            "student": student_profile,
            "program": program,
            "course_history": course_history,
            "courses": courses,
            "completed_credits": completed_credits,
            "total_credits": total_credits,
            "remaining_credits": remaining_credits,
            "progress_percent": min(progress_percent, 100),
            "core_course_count": len(core_courses),
            "elective_option_count": len(elective_courses),
            "elective_credits_required": max(total_credits - core_credits_required, 0),
            "elective_courses_required": max(total_credits - core_credits_required, 0) // 3,
            "completed_count": completed_count,
            "plans": all_plans,
        }

    def get_student_progress(self, user_id: int, status_filter: str = "all") -> dict[str, Any]:
        dashboard = self.get_student_dashboard(user_id)
        student = dashboard["student"]
        requirements = self.repo.get_program_requirements(student.program_id) if student.program_id else []
        program_course_ids = {requirement.course_id for requirement in requirements}
        courses = [
            course
            for course in dashboard["courses"].values()
            if not program_course_ids or course.id in program_course_ids
        ]

        history_by_course: dict[int, list[Any]] = {}
        for entry in dashboard["course_history"]:
            history_by_course.setdefault(entry.course_id, []).append(entry)

        course_rows = []
        for course in courses:
            attempts = history_by_course.get(course.id, [])
            if any(entry.completion_status == "completed" for entry in attempts):
                course_status = "completed"
            elif any(entry.completion_status == "in_progress" for entry in attempts):
                course_status = "in_progress"
            else:
                course_status = "not_started"
            if status_filter == "all" or course_status == status_filter:
                course_rows.append({"course": course, "status": course_status})

        return {
            "program": dashboard["program"],
            "courses": course_rows,
            "status_filter": status_filter,
            "counts": {
                "all": len(courses),
                "completed": sum(
                    any(entry.completion_status == "completed" for entry in history_by_course.get(course.id, []))
                    for course in courses
                ),
                "in_progress": sum(
                    not any(entry.completion_status == "completed" for entry in history_by_course.get(course.id, []))
                    and any(entry.completion_status == "in_progress" for entry in history_by_course.get(course.id, []))
                    for course in courses
                ),
            },
        }

    def add_course_to_draft(self, course_ids: list[int], course_id: int) -> list[int]:
        course = self.repo.get_course(course_id)

        if course is None:
            raise ValueError("Course not found")

        updated_draft = list(dict.fromkeys(course_ids))

        if course_id not in updated_draft:
            updated_draft.append(course_id)

        return updated_draft

    def get_plan_review(self, user_id: int, course_ids: list[int]) -> dict[str, Any]:
        dashboard = self.get_student_dashboard(user_id)
        selected_courses = []
        completed_course_ids = {
            entry.course_id
            for entry in dashboard["course_history"]
            if entry.completion_status == "completed"
        }

        for course_id in dict.fromkeys(course_ids):
            course = dashboard["courses"].get(course_id)
            if course is None:
                raise ValueError("A selected course is no longer available")
            prerequisites = self.repo.get_course_prerequisites(course_id)
            selected_courses.append({
                "course": course,
                "prerequisites_met": all(
                    prerequisite.required_course_id in completed_course_ids
                    for prerequisite in prerequisites
                ),
            })

        if not selected_courses:
            raise ValueError("Select at least one course")

        return {
            "courses": selected_courses,
            "total_credits": sum(row["course"].credits for row in selected_courses),
        }

    def get_student_plan(self, user_id: int, plan_id: int) -> dict[str, Any]:
        student = self.repo.get_student_profile_for_user(user_id)
        plan = self.repo.get_plan_by_id(plan_id)
        if student is None or plan is None or plan.student_id != student.id:
            raise ValueError("Plan not found")

        courses = [
            course
            for row in self.repo.get_plan_courses(plan.id)
            if (course := self.repo.get_course(row.course_id)) is not None
        ]
        return {
            "plan": plan,
            "courses": courses,
            "total_credits": sum(course.credits for course in courses),
        }

    def create_plan(
        self,
        user_id: int,
        semester: str,
        academic_year: str,
        course_ids: list[int],
        student_comments: str | None = None,
    ) -> dict[str, Any]:
        self.repo.seed_demo_data()
        student_profile = self.repo.get_student_profile_for_user(user_id)
        if student_profile is None:
            raise ValueError("Student profile not found")
        if not course_ids:
            raise ValueError("Select at least one course")

        advisor_profile = self.repo.get_advisor_profile_for_user_by_username("admin")
        if advisor_profile is None:
            user = self.repo.get_user_by_username("admin")
            if user is not None:
                advisor_profile = self.repo.create_advisor_profile(user.id, "Admin", "Advisor")
            else:
                raise ValueError("Advisor user not found")

        plan = self.repo.create_plan(
            student_id=student_profile.id,
            advisor_id=advisor_profile.id,
            semester=semester,
            academic_year=academic_year,
            course_ids=course_ids,
            student_comments=student_comments,
        )
        return {"plan": plan}

    def get_advisor_dashboard(self, user_id: int) -> dict[str, Any]:
        self.repo.seed_demo_data()
        advisor_profile = self.repo.get_advisor_profile_for_user(user_id)
        if advisor_profile is None:
            advisor_profile = self.repo.create_advisor_profile(user_id=user_id, first_name="Advisor", last_name="User")

        pending_plans = self.repo.get_plans_by_status("pending", advisor_profile.id)
        plan_summaries = []
        for plan in pending_plans:
            course_rows = self.repo.get_plan_courses(plan.id)
            course_list = [self.repo.get_course(row.course_id) for row in course_rows]
            plan_summaries.append({
                "plan": plan,
                "courses": [course for course in course_list if course is not None],
            })
        counts = {
            approval_status: len(self.repo.get_plans_by_status(approval_status, advisor_profile.id))
            for approval_status in ("pending", "approved", "rejected")
        }
        return {"advisor": advisor_profile, "plans": plan_summaries, "counts": counts}

    def get_advisor_plans_by_status(self, user_id: int, approval_status: str) -> dict[str, Any]:
        self.repo.seed_demo_data()

        advisor_profile = self.repo.get_advisor_profile_for_user(user_id)
        if advisor_profile is None:
            advisor_profile = self.repo.create_advisor_profile(
                user_id=user_id,
                first_name="Advisor",
                last_name="User"
            )

        plans = self.repo.get_plans_by_status(approval_status, advisor_profile.id)

        plan_summaries = []
        for plan in plans:
            course_rows = self.repo.get_plan_courses(plan.id)
            course_list = [self.repo.get_course(row.course_id) for row in course_rows]

            plan_summaries.append({
                "plan": plan,
                "courses": [course for course in course_list if course is not None],
            })

        return {"advisor": advisor_profile, "plans": plan_summaries}

    def get_advisor_profile(self, user_id: int) -> Any:
        advisor_profile = self.repo.get_advisor_profile_for_user(user_id)
        if advisor_profile is None:
            advisor_profile = self.repo.create_advisor_profile(
                user_id=user_id,
                first_name="Advisor",
                last_name="User",
            )
        return advisor_profile

    def review_plan(self, plan_id: int, user_id: int, decision: str, feedback: str | None) -> dict[str, Any]:
        self.repo.seed_demo_data()
        advisor_profile = self.repo.get_advisor_profile_for_user(user_id)
        if advisor_profile is None:
            advisor_profile = self.repo.create_advisor_profile(user_id=user_id, first_name="Advisor", last_name="User")

        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be approved or rejected")
        if decision == "rejected" and not (feedback or "").strip():
            raise ValueError("Rejection feedback is required")

        plan = self.repo.get_plan_by_id(plan_id)
        if plan is None:
            raise ValueError("Plan not found")

        self.repo.update_plan_status(plan.id, decision)
        self.repo.create_review(plan.id, advisor_profile.id, decision, feedback or "")
        return {"plan": plan, "decision": decision}

    def get_plan_view(self, plan_id: int) -> dict[str, Any]:
        plan = self.repo.get_plan_by_id(plan_id)
        if plan is None:
            raise ValueError("Plan not found")
        student = self.repo.get_student_profile(plan.student_id)
        if student is None:
            raise ValueError("Student profile not found")
        program = self.repo.get_degree_program(student.program_id) if student.program_id else None
        course_rows = self.repo.get_plan_courses(plan.id)
        completed_course_ids = {
            entry.course_id
            for entry in self.repo.get_student_course_history(student.id)
            if entry.completion_status == "completed"
        }
        courses = []
        for row in course_rows:
            course = self.repo.get_course(row.course_id)
            if course is None:
                continue
            prerequisites = self.repo.get_course_prerequisites(course.id)
            courses.append({
                "course": course,
                "prerequisites_met": all(
                    prerequisite.required_course_id in completed_course_ids
                    for prerequisite in prerequisites
                ),
            })
        return {
            "plan": plan,
            "student": student,
            "program": program,
            "courses": courses,
            "total_credits": sum(row["course"].credits for row in courses),
        }
