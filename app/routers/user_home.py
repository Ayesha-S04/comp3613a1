from fastapi import Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.advising import AdvisingRepository
from app.services.advising_service import AdvisingService
from app.utilities.flash import flash
from . import router, templates


@router.get("/app", response_class=HTMLResponse, name="user_home_view")
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    repo = AdvisingRepository(db)
    service = AdvisingService(repo)
    dashboard = service.get_student_dashboard(user.id)
    return templates.TemplateResponse(
        request=request,
        name="student-dashboard.html",
        context={
            "user": user,
            "dashboard": dashboard,
        },
    )


@router.get("/app/progress", response_class=HTMLResponse, name="student_progress_view")
async def student_progress_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    status_filter: str = "all",
):
    if status_filter not in {"all", "completed", "in_progress"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown course status filter")

    progress = AdvisingService(AdvisingRepository(db)).get_student_progress(user.id, status_filter)
    return templates.TemplateResponse(
        request=request,
        name="student-progress.html",
        context={
            "user": user,
            "progress": progress,
        },
    )


@router.get("/app/plan/new", response_class=HTMLResponse, name="student_plan_form")
async def student_plan_form(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    repo = AdvisingRepository(db)
    service = AdvisingService(repo)
    dashboard = service.get_student_dashboard(user.id)
    draft_course_ids = request.session.get(f"draft_course_ids_{user.id}", [])
    selected_courses = [
        dashboard["courses"][course_id]
        for course_id in draft_course_ids
        if course_id in dashboard["courses"]
    ]
    return templates.TemplateResponse(
        request=request,
        name="create-plan.html",
        context={
            "user": user,
            "courses": sorted(dashboard["courses"].values(), key=lambda course: course.code),
            "selected_courses": selected_courses,
            "selected_course_ids": [course.id for course in selected_courses],
            "draft_credits": sum(course.credits for course in selected_courses),
            "semester": request.session.get(f"draft_semester_{user.id}", ""),
            "academic_year": request.session.get(f"draft_academic_year_{user.id}", "2025/2026"),
        },
    )


@router.post("/app/plan/course/add", name="student_plan_add_course")
async def student_plan_add_course(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    course_id: int = Form(...),
    semester: str | None = Form(None),
    academic_year: str | None = Form(None),
):
    service = AdvisingService(AdvisingRepository(db))

    course_ids = request.session.get(f"draft_course_ids_{user.id}", [])
    already_added = course_id in course_ids

    try:
        updated_draft = service.add_course_to_draft(course_ids, course_id)
        request.session[f"draft_course_ids_{user.id}"] = updated_draft
        if semester:
            request.session[f"draft_semester_{user.id}"] = semester
        if academic_year:
            request.session[f"draft_academic_year_{user.id}"] = academic_year
        flash(
            request,
            "Course is already in your plan." if already_added else "Course added to your plan.",
            "info" if already_added else "success",
        )

    except ValueError as exc:
        flash(request, str(exc), "danger")

    return RedirectResponse(
        url=request.url_for("student_plan_form"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/app/plan/review", name="student_plan_review_start")
async def student_plan_review_start(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    semester: str = Form(...),
    academic_year: str = Form(...),
):
    service = AdvisingService(AdvisingRepository(db))
    course_ids = request.session.get(f"draft_course_ids_{user.id}", [])
    request.session[f"draft_semester_{user.id}"] = semester
    request.session[f"draft_academic_year_{user.id}"] = academic_year

    try:
        service.get_plan_review(user.id, course_ids)
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("student_plan_form"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=request.url_for("student_plan_review"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/app/plan/review", response_class=HTMLResponse, name="student_plan_review")
async def student_plan_review(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = AdvisingService(AdvisingRepository(db))
    course_ids = request.session.get(f"draft_course_ids_{user.id}", [])
    try:
        review = service.get_plan_review(user.id, course_ids)
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("student_plan_form"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    semester = request.session.get(f"draft_semester_{user.id}")
    academic_year = request.session.get(f"draft_academic_year_{user.id}")
    if not semester or not academic_year:
        flash(request, "Choose a semester and academic year before reviewing your plan.", "danger")
        return RedirectResponse(
            url=request.url_for("student_plan_form"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="student-plan-review.html",
        context={
            "user": user,
            "review": review,
            "semester": semester,
            "academic_year": academic_year,
        },
    )


@router.post("/app/plan/submit", name="student_plan_submit")
async def student_plan_submit(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    student_comments: str = Form(""),
):
    service = AdvisingService(AdvisingRepository(db))
    course_ids = request.session.get(f"draft_course_ids_{user.id}", [])
    semester = request.session.get(f"draft_semester_{user.id}")
    academic_year = request.session.get(f"draft_academic_year_{user.id}")

    if not semester or not academic_year:
        flash(request, "Review your plan and choose a semester before submitting.", "danger")
        return RedirectResponse(
            url=request.url_for("student_plan_form"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        result = service.create_plan(
            user.id,
            semester,
            academic_year,
            course_ids,
            student_comments.strip() or None,
        )
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("student_plan_form"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    request.session.pop(f"draft_course_ids_{user.id}", None)
    request.session.pop(f"draft_semester_{user.id}", None)
    request.session.pop(f"draft_academic_year_{user.id}", None)
    return RedirectResponse(
        url=request.url_for("student_plan_confirmation", plan_id=result["plan"].id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/app/plan/{plan_id}/submitted",
    response_class=HTMLResponse,
    name="student_plan_confirmation",
)
async def student_plan_confirmation(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    plan_id: int,
):
    try:
        plan_data = AdvisingService(AdvisingRepository(db)).get_student_plan(user.id, plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="student-plan-submitted.html",
        context={
            "user": user,
            **plan_data,
        },
    )


@router.get(
    "/app/plans/{plan_id}",
    response_class=HTMLResponse,
    name="student_plan_detail",
)
async def student_plan_detail(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    plan_id: int,
):
    try:
        plan_data = AdvisingService(AdvisingRepository(db)).get_student_plan(user.id, plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="student-plan-detail.html",
        context={
            "user": user,
            **plan_data,
        },
    )
