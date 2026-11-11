# Unit Test Plan

PDF upload tests use the shared `generic_pdf` fixture from `tests/conftest.py`, which generates a minimal one-page PDF. Invalid-content and size-limit cases deliberately alter or replace that fixture to exercise validation.

| Unit Test | Input | Expected Output |
|---|---|---|
| `test_check_password()` | A `User` with a hashed password; check using the original password. | Returns `True`. The stored password is not equal to the plaintext password. |
| `test_check_password_wrong_value()` | A `User` with a hashed password; check using a different password. | Returns `False`. |
| `test_authenticate_user_success()` | Existing username and matching password. | Returns a non-empty signed access token. |
| `test_authenticate_user_invalid_password()` | Existing username and incorrect password. | Returns `None`. |
| `test_authenticate_user_unknown_username()` | Username not present in the user repository. | Returns `None`. |
| `test_create_vacancy_trims_fields()` | Company ID `7`; title `"  Summer Intern  "`; description `"  Assist the team  "`; location `"  Port of Spain  "`; field `"Technology"`; status `"Published"`. | Repository receives a vacancy with trimmed title, description, and location; `status == "Published"` and `is_published is True`. |
| `test_create_vacancy_defaults_to_draft()` | Valid company, title, description, location, and field; omit status. | Repository receives a vacancy with `status == "Draft"` and `is_published is False`. |
| `test_create_vacancy_rejects_empty_title()` | Valid vacancy data with title containing only spaces. | Raises `ValueError` with `"Vacancy title is required."`; repository create is not called. |
| `test_create_vacancy_rejects_empty_description()` | Valid vacancy data with empty description. | Raises `ValueError` with `"Vacancy description is required."`; repository create is not called. |
| `test_create_vacancy_rejects_unsupported_field()` | Valid vacancy data with field of study `"Underwater Basketry"`. | Raises `ValueError` with `"Choose a valid field of study."`; repository create is not called. |
| `test_create_vacancy_rejects_invalid_status()` | Valid vacancy data with status `"Archived"`. | Raises `ValueError` indicating the status must be `Published`, `Closed`, or `Draft`; repository create is not called. |
| `test_update_vacancy_rejects_non_owner()` | Vacancy `12` belongs to company `7`; update requested by company `8`. | Raises `ValueError` with `"Vacancy not found."`; repository update is not called. |
| `test_update_published_vacancy_with_applicants_cannot_become_draft()` | Owned vacancy is `Published`, has applications, requested status is `Draft`. | Returned result has `draft_status_blocked is True`; vacancy remains `Published` and `is_published is True`. |
| `test_closing_vacancy_moves_applications_under_review()` | Owned open vacancy has applications; update its status to `Closed`. | Repository update is called with application status `Under Review`; returned vacancy is `Closed` and not published. |
| `test_browse_internships_rejects_company_user()` | Company user calls `InternshipService.browse(...)`. | Raises `ValueError` with `"Only student accounts can browse internships."`; internship repository is not queried. |
| `test_browse_internships_filters_supported_fields()` | Student user; query `"design"`; fields `["Technology", "not-a-field"]`; page `2`. | Repository receives query `"design"`, only supported field `"Technology"`, and page `2`; result includes the selected supported field. |
| `test_apply_creates_submitted_application_with_pdf()` | Student user; published vacancy `12`; no existing application; filename `"resume.pdf"`; content begins with `%PDF-`. | Repository creates an application for that student and vacancy with status `Submitted`, and a linked PDF document with the original safe filename and matching byte size. |
| `test_apply_rejects_non_student()` | Company user calls `InternshipService.apply(...)`. | Raises `ValueError` with `"Only student accounts can apply to internships."`; repositories are not asked to create an application. |
| `test_apply_rejects_unpublished_vacancy()` | Student user; vacancy is missing or not published. | Raises `ValueError` with `"This internship is no longer accepting applications."`; no application or document is created. |
| `test_apply_rejects_duplicate_application()` | Student already has an application for the published vacancy. | Raises `ValueError` with `"You have already applied to this internship."`; no document is stored and repository create is not called. |
| `test_application_document_rejects_non_pdf()` | Filename `"resume.docx"` with non-empty file content. | Raises `ValueError` indicating the document must be a PDF. |
| `test_application_document_rejects_invalid_pdf_content()` | Filename `"resume.pdf"` with content that does not begin with `%PDF-`. | Raises `ValueError` with `"The uploaded file is not a valid PDF document."`. |
| `test_application_document_rejects_empty_content()` | Filename `"resume.pdf"` and empty content. | Raises `ValueError` with `"The selected PDF is empty."`. |
| `test_application_document_rejects_file_over_10_mb()` | Valid PDF content larger than 10 MB. | Raises `ValueError` with `"Application documents must be 10 MB or smaller."`. |
| `test_replace_document_only_for_submitted_application()` | Student owns an application whose status is `Under Review`. | Raises `ValueError` with `"Only applications with Submitted status can be edited."`; replacement repository method is not called. |
| `test_replace_document_for_submitted_application()` | Student owns a `Submitted` application and supplies a valid PDF. | Repository receives the replacement document metadata; service returns the updated application and removes the old file only when it is inside the application upload directory. |
| `test_delete_application_rejects_non_student()` | Company user calls `InternshipService.delete_application(...)`. | Raises `ValueError` with `"Only student accounts can delete their applications."`; repository delete is not called. |
| `test_delete_application_rejects_application_not_owned_by_student()` | Student requests deletion of an application not found for their user ID. | Raises `ValueError` with `"Application not found."`; no application or document is removed. |
| `test_list_student_applications_rejects_company_user()` | Company user calls `ApplicationService.list_for_student(...)`. | Raises `ValueError` with `"Only student accounts can view their applications."`; application repository is not queried. |
| `test_browse_applications_rejects_non_owner()` | Company user requests applications for a vacancy owned by another company. | Raises `ValueError` with `"Vacancy not found."`; application list query is not run. |
| `test_browse_applications_ignores_unsupported_filters()` | Owning company requests applications with unsupported education level and status filters. | Result clears unsupported filters to `None` and repository receives no unsupported filter values. |
| `test_shortlist_application()` | Owning company, vacancy `12`, application `35` belongs to that vacancy. | Repository saves the application with status `Shortlisted`. |
| `test_reject_application()` | Owning company, vacancy `12`, application `35` belongs to that vacancy. | Repository saves the application with status `Rejected`. |
| `test_finish_review_rejects_only_under_review_applications()` | Vacancy has applications in `Under Review`, `Shortlisted`, and `Rejected` statuses. | Repository changes only `Under Review` applications to `Rejected` and returns the number changed. |
| `test_update_company_profile_requires_company_name()` | Company profile update has a blank or whitespace-only company name. | Raises `ValueError` with `"Company name is required."`; repository update is not called. |
| `test_update_student_profile_requires_student_account()` | User ID belongs to a company or does not exist. | Raises `ValueError` with `"Student profile not found."`; repository update is not called. |
| `test_update_student_profile_requires_first_and_last_name()` | Student profile update has a blank first name or last name. | Raises `ValueError` with `"First and last name are required."`; repository update is not called. |
| `test_local_document_path_rejects_path_outside_upload_directories()` | Document path resolves outside `app/uploads` and `app/static/uploads`. | Returns `None`; path is not returned for download. |
| `test_external_document_url_accepts_http_and_https()` | File paths `https://files.example.test/guide.pdf` and `http://files.example.test/guide.pdf`. | Returns the supplied URL for each valid HTTP or HTTPS URL. |
| `test_external_document_url_rejects_non_http_scheme()` | File path `javascript:alert(1)` or a relative local path. | Returns `None`. |

## Test Notes

- Run the implemented tests from the project root with `python -m pytest -q`.
- Test service rules with repository test doubles; repository query and transaction behavior should be tested separately against a temporary test database.
- Upload and cleanup tests use temporary directories so they do not alter application files.

## Pytest Implementation

The test cases are implemented under `tests/`: authentication and password checks, vacancy rules, internship browsing and applications, application review, profile validation, and document URL/path handling. Parameterized cases exercise multiple input variants. The suite currently has **44 passing cases** (`python -m pytest -q`).
