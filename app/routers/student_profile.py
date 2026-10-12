from fastapi import File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.user import UserRepository
from app.schemas.user import StudentProfileUpdate
from app.services.user_service import UserService
from app.utilities.company_profiles import save_uploaded_profile_image
from app.utilities.flash import flash
from . import router, templates


@router.get("/student/profile", response_class=HTMLResponse, name="student_profile_view")
async def student_profile_view(
    request: Request,
    user: AuthDep,
):
    if not user.is_student:
        return RedirectResponse(
            url=request.url_for("user_home_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="student_profile.html",
        context={"user": user},
    )


@router.post("/student/profile", response_class=HTMLResponse, name="student_profile_update")
async def student_profile_update(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    education_level: str = Form(""),
    profile_image: UploadFile | None = File(None),
):
    profile_image_url = None
    try:
        if profile_image and profile_image.filename:
            profile_image_url = save_uploaded_profile_image(
                await profile_image.read(),
                profile_image.content_type,
                user.username,
                profile_group="student_profiles",
            )

        profile_data = StudentProfileUpdate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            education_level=education_level,
        )
        UserService(UserRepository(db)).update_student_profile(
            user.id,
            profile_data,
            profile_image_url,
        )
        flash(request, "Student profile updated successfully.", "success")
    except ValueError as exc:
        flash(request, str(exc), "danger")
    except Exception:  # noqa: BLE001
        flash(request, "Unable to update your profile right now.", "danger")

    return RedirectResponse(
        url=request.url_for("student_profile_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
