from fastapi import File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.user import UserRepository
from app.schemas.user import UserProfileUpdate
from app.services.user_service import UserService
from app.utilities.company_profiles import save_uploaded_profile_image
from app.utilities.flash import flash
from . import router, templates


@router.get("/company/profile", response_class=HTMLResponse, name="company_profile_view")
async def company_profile_view(
    request: Request,
    user: AuthDep,
):
    return templates.TemplateResponse(
        request=request,
        name="company_profile.html",
        context={"user": user},
    )


@router.post("/company/profile", response_class=HTMLResponse, name="company_profile_update")
async def company_profile_update(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    location: str = Form(""),
    profile_image: UploadFile | None = File(None),
):
    profile_image_url = None
    try:
        if profile_image and profile_image.filename:
            profile_image_url = save_uploaded_profile_image(
                await profile_image.read(),
                profile_image.content_type,
                user.username,
            )

        profile_data = UserProfileUpdate(
            company_name=company_name,
            email=email,
            phone=phone,
            location=location,
        )
        UserService(UserRepository(db)).update_profile(
            user.id,
            profile_data,
            profile_image_url,
        )
        flash(request, "Company profile updated successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    except Exception:
        flash(request, "Unable to update the company profile right now.", "danger")

    return RedirectResponse(
        url=request.url_for("company_profile_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )