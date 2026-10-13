#!/usr/bin/env python3
"""FastStarter project CLI — stdlib argparse (no extra CLI library).

From the project root (venv active, deps installed; ``.env`` optional — falls back to ``.env.example``):

    python manage.py init
    python manage.py run
    python manage.py users
    python manage.py report --name "Student Name" --id "816000000"
    python manage.py usecase
    python manage.py skills-verify
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path


def _ensure_models_loaded() -> None:
    import app.models  # noqa: F401


def cmd_init(args: argparse.Namespace) -> None:
    """Create database tables (drops existing by default) and seed demo users."""
    from app.config import get_settings
    from app.database import drop_all, ensure_db_and_tables

    _ensure_models_loaded()
    if args.drop:
        print("Dropping all tables…")
        # Drop can fail on a brand-new empty DB; create path still retries.
        try:
            drop_all()
        except Exception as exc:  # noqa: BLE001
            from app.database import is_db_not_ready_error

            if not is_db_not_ready_error(exc):
                raise
            print(f"Database not ready yet while dropping ({exc}); continuing…")
    print("Creating tables…")
    ensure_db_and_tables()
    print(f"Database ready ({get_settings().database_uri}).")
    if getattr(args, "seed", True):
        cmd_seed(args)


def cmd_seed(args: argparse.Namespace) -> None:
    """Insert demo users, companies, vacancies, students, and applications.

    bob / bobpass       (regular_user)
    admin / adminpass   (admin)
    company01 / company01pass through company10 / company10pass (company)
    student01 / student01pass through student10 / student10pass (student)
    """
    from app.database import ensure_db_and_tables, get_cli_session
    from app.repositories.application import ApplicationRepository
    from app.models.vacancy import InternshipVacancy
    from app.repositories.user import UserRepository
    from app.repositories.vacancy import VacancyRepository
    from app.schemas.user import (
        AdminCreate,
        CompanyCreate,
        RegularUserCreate,
        StudentCreate,
        StudentProfileUpdate,
        UserProfileUpdate,
    )
    from app.utilities.company_profiles import ensure_company_profile_image
    from app.utilities.security import encrypt_password

    _ensure_models_loaded()
    ensure_db_and_tables()

    demo_users = [
        ("bob", "bob@example.com", "bobpass", "regular_user"),
        ("admin", "admin@example.com", "adminpass", "admin"),
    ]

    company_seed = [
        ("Northstar Business Group", "Business", "Toronto", [
            "Business Operations Intern", "Market Research Intern",
            "Finance Intern", "Human Resources Intern",
        ]),
        ("BlueRiver Science Labs", "Science", "Vancouver", [
            "Laboratory Research Intern", "Environmental Science Intern",
            "Data Science Intern", "Biology Research Intern",
        ]),
        ("Vertex Technology Co.", "Technology", "Montreal", [
            "Software Engineering Intern", "Cybersecurity Intern",
            "Cloud Infrastructure Intern", "Product Support Intern",
        ]),
        ("Harvest Field Cooperative", "Agriculture", "Saskatoon", [
            "Agricultural Technology Intern", "Crop Research Intern",
            "Farm Operations Intern", "Food Supply Intern",
        ]),
        ("Summit Sports Network", "Sports", "Calgary", [
            "Sports Marketing Intern", "Athlete Development Intern",
            "Sports Analytics Intern", "Event Operations Intern",
        ]),
        ("Ironwood Engineering", "Engineering", "Edmonton", [
            "Mechanical Engineering Intern", "Civil Engineering Intern",
            "Electrical Engineering Intern", "Manufacturing Intern",
        ]),
        ("Cedar Green Energy", "Energy", "Halifax", [
            "Renewable Energy Intern", "Power Systems Intern",
            "Sustainability Intern", "Energy Policy Intern",
        ]),
        ("Brightline Creative Studio", "Creative", "Ottawa", [
            "Graphic Design Intern", "Content Strategy Intern",
            "User Experience Intern", "Digital Production Intern",
        ]),
        ("Harbor Health Partners", "Health", "Victoria", [
            "Public Health Intern", "Healthcare Administration Intern",
            "Clinical Research Intern", "Health Communications Intern",
        ]),
        ("Pioneer Logistics Hub", "Logistics", "Winnipeg", [
            "Supply Chain Intern", "Transportation Planning Intern",
            "Warehouse Operations Intern", "Procurement Intern",
        ]),
        ("Meridian Media Collective", "Media", "Kingston", [
            "Editorial Intern", "Social Media Intern",
            "Brand Strategy Intern", "Video Production Intern",
        ]),
        ("Lakeside Legal Partners", "Law", "Regina", [
            "Legal Research Intern", "Corporate Law Intern",
            "Family Law Intern", "Contract Administration Intern",
        ]),
        ("Nimbus Air Services", "Aviation", "Kelowna", [
            "Flight Operations Intern", "Ground Services Intern",
            "Airport Management Intern", "Safety Systems Intern",
        ]),
        ("Dune & Coast Hospitality", "Hospitality", "Charlottetown", [
            "Guest Experience Intern", "Event Planning Intern",
            "Food & Beverage Intern", "Revenue Management Intern",
        ]),
        ("Atlantic Retail Group", "Retail", "St. John's", [
            "Merchandising Intern", "Customer Insights Intern",
            "E-commerce Intern", "Store Operations Intern",
        ]),
        ("Terraform Urban Design", "Architecture", "Quebec City", [
            "Urban Planning Intern", "Landscape Design Intern",
            "Architectural Drafting Intern", "Project Coordination Intern",
        ]),
        ("Cobalt Financial Advisory", "Finance", "Calgary", [
            "Investment Analyst Intern", "Risk Assessment Intern",
            "Tax Advisory Intern", "Wealth Management Intern",
        ]),
        ("Northwood Community Health", "Healthcare", "Hamilton", [
            "Patient Services Intern", "Compliance Intern",
            "Care Coordination Intern", "Health Data Intern",
        ]),
        ("Summit Robotics Lab", "Robotics", "Mississauga", [
            "Robotics Software Intern", "Systems Integration Intern",
            "Industrial Automation Intern", "Control Systems Intern",
        ]),
        ("Evergreen Advisory Group", "Consulting", "Ottawa", [
            "Business Consulting Intern", "Operations Analyst Intern",
            "Market Entry Intern", "Client Experience Intern",
        ]),
    ]

    for number, (name, discipline, location, titles) in enumerate(company_seed, start=1):
        demo_users.append(
            (
                f"company{number:02d}",
                f"company{number:02d}@example.com",
                f"company{number:02d}pass",
                "company",
            )
        )

    created = 0
    skipped = 0
    vacancies_created = 0
    vacancies_skipped = 0
    students_created = 0
    students_skipped = 0
    applications_created = 0
    applications_skipped = 0
    applications_removed = 0
    documents_created = 0
    with get_cli_session() as session:
        repo = UserRepository(session)
        vacancy_repo = VacancyRepository(session)
        application_repo = ApplicationRepository(session)
        for username, email, password, role in demo_users:
            user = repo.get_by_username(username)
            if user:
                print(f"  skip  {username} (already exists)")
                skipped += 1
            else:
                payload_cls = {
                    "admin": AdminCreate,
                    "company": CompanyCreate,
                }.get(role, RegularUserCreate)
                user = repo.create(
                    payload_cls(
                        username=username,
                        email=email,
                        password=encrypt_password(password),
                        role=role,
                    )
                )
                print(f"  create {username} ({role})")
                created += 1

            if role != "company":
                continue

            company_number = int(username.removeprefix("company"))
            company_name, discipline, location, titles = company_seed[company_number - 1]
            profile_image_url = ensure_company_profile_image(
                username,
                company_name,
                discipline,
            )
            repo.update_profile(
                user.id,
                UserProfileUpdate(
                    company_name=company_name,
                    email=user.email,
                    location=location,
                ),
                profile_image_url,
            )
            for title in titles:
                existing_vacancy = vacancy_repo.get_by_company_and_title(user.id, title)
                if existing_vacancy:
                    if not existing_vacancy.field_of_study:
                        existing_vacancy.field_of_study = discipline
                        vacancy_repo.update(existing_vacancy)
                    vacancies_skipped += 1
                    continue
                vacancy_repo.create(
                    InternshipVacancy(
                        company_id=user.id,
                        title=title,
                        description=(
                            f"Join {company_name}'s {discipline.lower()} team "
                            f"and gain practical experience through a guided internship."
                        ),
                        location=location,
                        field_of_study=discipline,
                        status="Published",
                    )
                )
                vacancies_created += 1

        student_seed = [
            ("Avery", "Morgan", "3rd Year Undergraduate"),
            ("Jordan", "Lee", "Associate's Degree Graduate"),
            ("Taylor", "Patel", "2nd Year Postgraduate"),
            ("Riley", "Chen", "1st Year Undergraduate"),
            ("Casey", "Rivera", "4th Year Undergraduate"),
            ("Morgan", "Bennett", "1st Year Postgraduate"),
            ("Quinn", "Singh", "3rd Year Undergraduate"),
            ("Cameron", "Brooks", "Associate's Degree Graduate"),
            ("Drew", "Wilson", "2nd Year Undergraduate"),
            ("Parker", "Martin", "1st Year Undergraduate"),
            ("Harper", "Ward", "2nd Year Undergraduate"),
            ("Sage", "Patel", "3rd Year Undergraduate"),
            ("Mila", "Nguyen", "1st Year Postgraduate"),
            ("Emerson", "Thompson", "4th Year Undergraduate"),
            ("Skyler", "Ali", "Associate's Degree Graduate"),
            ("Noah", "Gonzalez", "2nd Year Postgraduate"),
            ("Ari", "Scott", "3rd Year Undergraduate"),
            ("Blake", "Brown", "1st Year Undergraduate"),
            ("Ellis", "Kim", "4th Year Undergraduate"),
            ("Rowan", "Young", "2nd Year Postgraduate"),
            ("Jamie", "Johnson", "Associate's Degree Graduate"),
            ("Dakota", "Hall", "3rd Year Undergraduate"),
            ("Finley", "Adams", "1st Year Undergraduate"),
            ("Reese", "Flores", "3rd Year Undergraduate"),
            ("Bailey", "Norris", "2nd Year Undergraduate"),
            ("Morgan", "Miller", "4th Year Undergraduate"),
            ("Alex", "Perez", "Associate's Degree Graduate"),
            ("Chris", "Roberts", "2nd Year Postgraduate"),
            ("Harley", "Turner", "1st Year Undergraduate"),
            ("Remy", "Campbell", "3rd Year Undergraduate"),
            ("Jordan", "Hernandez", "2nd Year Undergraduate"),
            ("Taylor", "Evans", "4th Year Undergraduate"),
            ("Peyton", "Green", "Associate's Degree Graduate"),
            ("Carter", "Hill", "1st Year Postgraduate"),
            ("Sawyer", "Baker", "3rd Year Undergraduate"),
            ("Parker", "Rivera", "2nd Year Undergraduate"),
            ("Rory", "King", "4th Year Undergraduate"),
            ("Casey", "Price", "Associate's Degree Graduate"),
            ("Sam", "Wright", "1st Year Undergraduate"),
            ("Jules", "Long", "3rd Year Undergraduate"),
            ("Kendall", "Ross", "2nd Year Postgraduate"),
            ("Riley", "Hughes", "4th Year Undergraduate"),
            ("Sydney", "Cooper", "Associate's Degree Graduate"),
            ("Devon", "Peterson", "1st Year Undergraduate"),
            ("Shay", "Gray", "3rd Year Undergraduate"),
            ("Ashton", "Ramirez", "2nd Year Undergraduate"),
            ("Hayden", "James", "4th Year Undergraduate"),
            ("Logan", "Bennett", "1st Year Postgraduate"),
            ("Avery", "Foster", "3rd Year Undergraduate"),
            ("Charlie", "Moore", "2nd Year Undergraduate"),
        ]
        student_users = []
        for number, (first_name, last_name, education_level) in enumerate(student_seed, start=1):
            username = f"student{number:02d}"
            user = repo.get_by_username(username)
            if user:
                students_skipped += 1
            else:
                user = repo.create(
                    StudentCreate(
                        username=username,
                        email=f"{username}@example.com",
                        password=encrypt_password(f"{username}pass"),
                        first_name=first_name,
                        last_name=last_name,
                        education_level=education_level,
                        profile_image_url=(
                            f"https://i.pravatar.cc/240?img={number}"
                        ),
                    )
                )
                students_created += 1
            repo.update_student_profile(
                user.id,
                StudentProfileUpdate(
                    first_name=first_name,
                    last_name=last_name,
                    email=user.email,
                    education_level=education_level,
                ),
            )
            student_users.append(user)

        published_vacancies = vacancy_repo.list_published()
        demo_document_path = (
            "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/"
            "resources/pdf/dummy.pdf"
        )
        student_ids = [student.id for student in student_users]
        applicant_map = {}
        rng = random.Random(42)
        for vacancy in published_vacancies:
            applicant_ids = rng.sample(student_ids, k=min(10, len(student_ids)))
            applicant_map[vacancy.id] = set(applicant_ids)

        for student in student_users:
            target_vacancy_ids = {
                vacancy_id
                for vacancy_id, applicant_ids in applicant_map.items()
                if student.id in applicant_ids
            }
            applications_removed += application_repo.remove_seeded_applications_not_in_targets(
                student_id=student.id,
                target_vacancy_ids=target_vacancy_ids,
                demo_document_path=demo_document_path,
            )

        for vacancy in published_vacancies:
            applicant_ids = sorted(applicant_map.get(vacancy.id, set()))
            for student_id in applicant_ids:
                application = application_repo.get_by_student_and_vacancy(
                    student_id,
                    vacancy.id,
                )
                if application:
                    applications_skipped += 1
                    continue

                application = application_repo.create_application(
                    student_id=student_id,
                    vacancy_id=vacancy.id,
                )
                document = application_repo.create_document(
                    name=f"student{student_id}-resume.pdf",
                    file_path=demo_document_path,
                )
                application_repo.attach_document(application.id, document.id)
                applications_created += 1
                documents_created += 1

    print(f"Seed done — created {created}, skipped {skipped}.")
    print(
        f"Vacancies — created {vacancies_created}, "
        f"skipped {vacancies_skipped}."
    )
    print(
        f"Students — created {students_created}, skipped {students_skipped}."
    )
    print(
        f"Applications — created {applications_created}, "
        f"skipped {applications_skipped}, old demo records replaced {applications_removed}; "
        f"documents created {documents_created}."
    )
    print("Login with bob/bobpass or admin/adminpass")
    print("Company logins use company01/company01pass through company10/company10pass")


def cmd_run(args: argparse.Namespace) -> None:
    """Start the FastAPI app with Uvicorn."""
    import uvicorn

    from app.config import get_settings

    settings = get_settings()
    bind_host = args.host or settings.app_host
    bind_port = args.port or settings.app_port
    if args.reload is None:
        use_reload = settings.env.lower() != "production"
    else:
        use_reload = args.reload
    print(f"Starting FastStarter on http://{bind_host}:{bind_port} (reload={use_reload})")
    uvicorn.run(
        "app.main:app",
        host=bind_host,
        port=bind_port,
        reload=use_reload,
    )


def cmd_report(args: argparse.Namespace) -> None:
    """Build the submission package: merge judge, package transcripts, write PDF.

    Guide must (1) write ``docs/judge.md`` and (2) pull every Guide chat into
    ``docs/transcripts/*.md`` before this command. Report only packages those files.
    """
    from app.report_pdf import export_report
    from app.skill_integrity import format_report, verify

    result = export_report(
        name=args.name,
        student_id=args.student_id,
        source=None if args.src is None else Path(args.src),
        output=None if args.output is None else Path(args.output),
    )
    print()
    print("Report package:")
    print(
        f"  Judge:       {'merged docs/judge.md' if result.judge_merged else 'MISSING - Guide must run student-judge first'}"
    )
    print(
        f"  Transcripts: {result.transcript_count} chat(s) in docs/transcripts/"
        + (
            ""
            if result.transcript_count
            else " (EMPTY - Guide must pull Copilot/Cursor/OpenCode chats first)"
        )
    )
    if result.transcript_zip:
        print(f"  Zip:         {result.transcript_zip.as_posix()}")
    print(f"  PDF:         {result.pdf_path.as_posix()}")
    print(format_report(verify()))


def cmd_transcripts(args: argparse.Namespace) -> None:
    """Package agent-written markdown under docs/transcripts/ (+ zip)."""
    from app.transcript_export import package_transcripts

    result = package_transcripts(make_zip=not args.no_zip)
    if result.found == 0:
        print(
            "Warning: no chat markdown in docs/transcripts/. "
            "The Guide agent must pull every Guide chat for this project "
            "(Copilot Agent, Cursor, or OpenCode) into docs/transcripts/<slug>.md first."
        )
        raise SystemExit(2)
    print(f"Submission package ready: {result.out_dir}")
    if result.zip_path:
        print(f"Zip for submission: {result.zip_path}")


def cmd_skills_verify(args: argparse.Namespace) -> None:
    """Check course skill files against .agents/skills.lock.json."""
    from app.skill_integrity import format_report, verify

    result = verify()
    print(format_report(result))
    if not result.ok:
        raise SystemExit(1)


def cmd_usecase(args: argparse.Namespace) -> None:
    """Render docs/diagrams/use-case.json to a UML use-case PNG."""
    from app.usecase_diagram import render_usecase_png

    dest = render_usecase_png(
        spec_path=None if args.spec is None else Path(args.spec),
        output=None if args.output is None else Path(args.output),
    )
    print(f"Wrote {dest}")


def cmd_skills_lock(args: argparse.Namespace) -> None:
    """Rewrite the skill lockfile (course authors only)."""
    from app.skill_integrity import write_lock

    dest = write_lock()
    print(f"Wrote {dest}")


def cmd_users(args: argparse.Namespace) -> None:
    """List users currently in the database."""
    from sqlmodel import select

    from app.database import get_cli_session
    from app.models.user import User

    _ensure_models_loaded()
    with get_cli_session() as session:
        users = session.exec(select(User)).all()
        if not users:
            print("No users found. Run: python manage.py init")
            return
        for user in users:
            print(
                f"  id={user.id}  username={user.username}  "
                f"role={user.role}  email={user.email}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python manage.py",
        description="FastStarter Python CLI — init database, seed demo data, run the app.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init",
        help="Create DB tables and seed demo users (drops existing tables by default)",
    )
    p_init.add_argument(
        "--no-drop",
        dest="drop",
        action="store_false",
        help="Create tables without dropping existing ones",
    )
    p_init.add_argument(
        "--no-seed",
        dest="seed",
        action="store_false",
        help="Skip demo user seed after creating tables",
    )
    p_init.set_defaults(drop=True, seed=True, func=cmd_init)

    p_seed = sub.add_parser(
        "seed",
        help="Insert demo users, companies, and vacancies (idempotent)",
    )
    p_seed.set_defaults(func=cmd_seed)

    p_run = sub.add_parser("run", help="Start the web app (uvicorn)")
    p_run.add_argument("--host", default=None, help="Bind host")
    p_run.add_argument("--port", type=int, default=None, help="Bind port")
    reload_group = p_run.add_mutually_exclusive_group()
    reload_group.add_argument(
        "--reload", dest="reload", action="store_true", default=None, help="Enable auto-reload"
    )
    reload_group.add_argument(
        "--no-reload", dest="reload", action="store_false", help="Disable auto-reload"
    )
    p_run.set_defaults(func=cmd_run, reload=None)

    p_users = sub.add_parser("users", help="List users in the database")
    p_users.set_defaults(func=cmd_users)

    p_report = sub.add_parser(
        "report",
        help=(
            "Build submission package: merge docs/judge.md, package docs/transcripts/, "
            "write docs/report.pdf (Guide pulls chats + runs student-judge first)"
        ),
    )
    p_report.add_argument("--name", required=True, help="Student name (printed on the PDF cover)")
    p_report.add_argument("--id", dest="student_id", required=True, help="Student ID (PDF only)")
    p_report.add_argument("--src", default=None, help="Markdown path (default: docs/report.md)")
    p_report.add_argument("--output", default=None, help="PDF path (default: docs/report.pdf)")
    p_report.set_defaults(func=cmd_report)

    p_transcripts = sub.add_parser(
        "transcripts",
        help="Package agent-written docs/transcripts/*.md into INDEX + zip (no IDE scrape)",
    )
    p_transcripts.add_argument(
        "--no-zip",
        action="store_true",
        help="Skip writing docs/transcripts.zip",
    )
    p_transcripts.set_defaults(func=cmd_transcripts)

    p_usecase = sub.add_parser(
        "usecase",
        help="Render docs/diagrams/use-case.json to a UML use-case PNG",
    )
    p_usecase.add_argument("--spec", default=None, help="JSON spec (default: docs/diagrams/use-case.json)")
    p_usecase.add_argument("--output", default=None, help="PNG path (default: docs/diagrams/use-case.png)")
    p_usecase.set_defaults(func=cmd_usecase)

    p_skills_verify = sub.add_parser(
        "skills-verify",
        help="Check course skills against .agents/skills.lock.json",
    )
    p_skills_verify.set_defaults(func=cmd_skills_verify)

    p_skills_lock = sub.add_parser(
        "skills-lock",
        help="Rewrite .agents/skills.lock.json (course authors; needs FASTSTARTER_SKILLS_LOCK=1)",
    )
    p_skills_lock.set_defaults(func=cmd_skills_lock)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])