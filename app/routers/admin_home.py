from fastapi import Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AdminDep, AuthDep
from app.dependencies.session import SessionDep
from app.repositories.advising import AdvisingRepository
from app.services.advising_service import AdvisingService
from app.utilities.flash import flash
from . import router, templates


@router.get("/admin/dashboard", response_class=HTMLResponse, name="advisor_dashboard_view")
async def advisor_dashboard_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    service = AdvisingService(AdvisingRepository(db))
    dashboard = service.get_advisor_dashboard(user.id)

    return templates.TemplateResponse(
        request=request,
        name="advisor-dashboard.html",
        context={
            "user": user,
            "dashboard": dashboard,
        },
    )


@router.get("/admin", response_class=HTMLResponse, name="admin_home_view")
async def admin_home_view(
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    dashboard = AdvisingService(AdvisingRepository(db)).get_advisor_dashboard(user.id)
    return templates.TemplateResponse(
        request=request,
        name="advisor-dashboard.html",
        context={
            "user": user,
            "dashboard": dashboard,
        },
    )


@router.get("/admin/plans/{approval_status}", response_class=HTMLResponse, name="advisor_plans_by_status_view")
async def advisor_plans_by_status_view(
    request: Request,
    approval_status: str,
    user: AdminDep,
    db: SessionDep,
):
    if approval_status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan status not found")

    result = AdvisingService(AdvisingRepository(db)).get_advisor_plans_by_status(
        user.id,
        approval_status,
    )
    return templates.TemplateResponse(
        request=request,
        name="advisor-plans.html",
        context={
            "user": user,
            "advisor": result["advisor"],
            "plans": result["plans"],
            "approval_status": approval_status,
        },
    )


@router.get("/profile", response_class=HTMLResponse, name="profile_view")
async def profile_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = AdvisingService(AdvisingRepository(db))
    if user.role == "admin":
        profile = service.get_advisor_profile(user.id)
        profile_type = "advisor"
    else:
        profile = service.get_student_dashboard(user.id)["student"]
        profile_type = "student"
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "user": user,
            "profile": profile,
            "profile_type": profile_type,
        },
    )


@router.get("/admin/plan/{plan_id}", response_class=HTMLResponse, name="plan_review_view")
async def plan_review_view(
    request: Request,
    plan_id: int,
    user: AdminDep,
    db: SessionDep,
):
    service = AdvisingService(AdvisingRepository(db))
    try:
        plan_view = service.get_plan_view(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="plan-review.html",
        context={
            "user": user,
            "plan": plan_view["plan"],
            "student": plan_view["student"],
            "program": plan_view["program"],
            "courses": plan_view["courses"],
            "total_credits": plan_view["total_credits"],
        },
    )


@router.post("/admin/plan/{plan_id}/review", response_class=HTMLResponse, name="plan_review_submit")
async def plan_review_submit(
    request: Request,
    plan_id: int,
    user: AdminDep,
    db: SessionDep,
    decision: str = Form(...),
    feedback: str = Form(""),
):
    service = AdvisingService(AdvisingRepository(db))
    try:
        service.review_plan(plan_id, user.id, decision, feedback.strip() or None)
    except ValueError as exc:
        if str(exc) == "Plan not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        flash(request, str(exc), "danger")
        plan_view = service.get_plan_view(plan_id)
        return templates.TemplateResponse(
            request=request,
            name="plan-review.html",
            context={
                "user": user,
                "plan": plan_view["plan"],
                "student": plan_view["student"],
                "program": plan_view["program"],
                "courses": plan_view["courses"],
                "total_credits": plan_view["total_credits"],
                "error_message": str(exc),
            },
        )

    return RedirectResponse(
        url=request.url_for("advisor_plan_confirmation", plan_id=plan_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/admin/plan/{plan_id}/confirmation",
    response_class=HTMLResponse,
    name="advisor_plan_confirmation",
)
async def advisor_plan_confirmation(
    request: Request,
    plan_id: int,
    user: AdminDep,
    db: SessionDep,
):
    try:
        plan_view = AdvisingService(AdvisingRepository(db)).get_plan_view(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if plan_view["plan"].approval_status not in {"approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan decision not found")

    return templates.TemplateResponse(
        request=request,
        name="advisor-plan-confirmation.html",
        context={
            "user": user,
            "plan": plan_view["plan"],
            "student": plan_view["student"],
            "decision": plan_view["plan"].approval_status,
        },
    )
