
import json
import subprocess
import sys

REPO = "nknet2004-p/student-academic-resource-platform"

STORIES = [
    ("US01: Student Registration", "High",
     "As a student, I want to create an account so that I can access the platform.",
     ["Accept a name, email and password.", "Validate required fields and email format.", "Reject duplicate email addresses.", "Store a salted password hash, never a plain-text password."]),

    ("US02: Student Login", "High",
     "As a student, I want to log in so that I can access my account.",
     ["Accept registered email and password.", "Verify the password securely.", "Reject invalid credentials.", "Display the student dashboard after successful login."]),

    ("US03: Student Logout", "Medium",
     "As a student, I want to log out so that my session ends.",
     ["Provide a logout option.", "Clear the active login session.", "Return the user to the login screen."]),

    ("US04: Manage Profile", "Medium",
     "As a student, I want to manage my profile so that my details remain current.",
     ["Display the student's profile.", "Allow permitted profile details to be updated.", "Validate updated information.", "Save changes successfully."]),

    ("US05: Upload Academic Resource", "High",
     "As a student, I want to upload academic material so that others can use it.",
     ["Require an authenticated user.", "Accept supported academic files.", "Reject empty or oversized files.", "Store the file and its metadata successfully."]),

    ("US06: Categorize Resources", "High",
     "As a student, I want to categorize uploads so that material is organized.",
     ["Select a subject.", "Select a semester.", "Select a resource type.", "Save the selected categories with the resource."]),

    ("US07: View Resource Details", "Medium",
     "As a student, I want to view resource details so that I can assess their usefulness.",
     ["Display the title and description.", "Show subject, semester and resource type.", "Show uploader and upload date where available."]),

    ("US08: Download Resource", "High",
     "As a student, I want to download resources so that I can study offline.",
     ["Provide a download option for available files.", "Preserve the original filename.", "Handle missing files gracefully.", "Track successful downloads accurately."]),

    ("US09: Edit Uploaded Resource", "Medium",
     "As a student, I want to edit my resource details so that I can correct mistakes.",
     ["Allow owners to edit their own metadata.", "Validate updated fields.", "Prevent unauthorized users from editing the resource.", "Save changes."]),

    ("US10: Delete Uploaded Resource", "Medium",
     "As a student, I want to delete my uploads so that outdated material can be removed.",
     ["Allow owners to delete their own resources.", "Prevent deletion by unauthorized users.", "Remove the resource record and associated file.", "Show a confirmation message."]),

    ("US11: Search Resources", "High",
     "As a student, I want to search by keyword so that I can find material quickly.",
     ["Search resource titles and descriptions.", "Display matching results.", "Handle searches with no matches.", "Allow the search to be cleared."]),

    ("US12: Filter by Subject", "Medium",
     "As a student, I want to filter resources by subject so that I see relevant material.",
     ["Provide a subject filter.", "Show resources matching the selected subject.", "Allow the filter to be reset."]),

    ("US13: Filter by Semester", "Medium",
     "As a student, I want to filter resources by semester so that I find course-relevant material.",
     ["Provide semester options.", "Show matching resources.", "Allow semester filtering to be combined with search."]),

    ("US14: Filter by Resource Type", "Medium",
     "As a student, I want to filter by resource type so that I can find notes or presentations.",
     ["Provide resource-type options.", "Show matching files.", "Allow the filter to be reset."]),

    ("US15: Sort Resources", "Medium",
     "As a student, I want to sort resources so that I can browse them conveniently.",
     ["Support sorting by upload date.", "Support sorting by popularity where available.", "Display results in the selected order."]),

    ("US16: Bookmark Resource", "Medium",
     "As a student, I want to bookmark useful resources so that I can revisit them.",
     ["Allow a logged-in student to bookmark a resource.", "Prevent duplicate bookmarks.", "Store bookmarks against the student account."]),

    ("US17: View Bookmarks", "Medium",
     "As a student, I want to view my bookmarks so that I can access saved resources.",
     ["Display the student's saved resources.", "Allow bookmarked resources to be opened or downloaded.", "Handle an empty bookmark list."]),

    ("US18: Rate Resource", "Medium",
     "As a student, I want to rate a resource so that I can share feedback.",
     ["Allow a rating within a defined range.", "Validate rating values.", "Associate the rating with the student and resource.", "Prevent unintended duplicate ratings."]),

    ("US19: View Resource Statistics", "Low",
     "As a student, I want to see resource popularity so that I can identify useful material.",
     ["Display available download counts.", "Display average ratings when ratings exist.", "Handle resources without ratings."]),

    ("US20: Report a Resource", "Medium",
     "As a student, I want to report inappropriate material so that it can be reviewed.",
     ["Provide a report option.", "Collect a report reason.", "Store the report for administrative review.", "Prevent empty report submissions."]),

    ("US21: Administrator Login", "High",
     "As an administrator, I want a protected admin login so that I can manage the platform.",
     ["Restrict administration to authorized accounts.", "Reject invalid credentials.", "Keep student accounts from receiving admin privileges automatically."]),

    ("US22: Manage Users", "Medium",
     "As an administrator, I want to manage registered users so that I can maintain the platform.",
     ["Display registered user information to authorized admins.", "Support appropriate account-management actions.", "Prevent unauthorized access to administration."]),

    ("US23: Moderate Resources", "High",
     "As an administrator, I want to review reported resources so that inappropriate content can be handled.",
     ["Display submitted reports.", "Allow authorized review.", "Allow inappropriate resources to be removed.", "Record the resulting moderation status."]),

    ("US24: Student Dashboard", "Medium",
     "As a student, I want a personal dashboard so that I can review my activity.",
     ["Display the student's uploads.", "Display available resource totals.", "Show relevant personal activity where available."]),

    ("US25: Admin Dashboard and Reports", "Medium",
     "As an administrator, I want platform statistics so that I can monitor usage.",
     ["Display user and resource totals.", "Display download and report statistics where available.", "Handle an empty database.", "Restrict dashboard access to administrators."])
]


def run_command(args, capture=False):
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=capture
    )


def main():
    try:
        run_command(["gh", "auth", "status"])
        run_command(["gh", "repo", "view", REPO])
    except FileNotFoundError:
        print("GitHub CLI (gh) was not found. Restart VS Code and try again.")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("GitHub authentication or repository access failed.")
        sys.exit(1)

    try:
        result = run_command(
            ["gh", "issue", "list", "--repo", REPO,
             "--state", "all", "--limit", "500",
             "--json", "title"],
            capture=True
        )
        existing = {
            item["title"]
            for item in json.loads(result.stdout)
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print("Could not retrieve existing issues. No issues were created.")
        sys.exit(1)

    created = 0
    skipped = 0

    for title, priority, story, criteria in STORIES:
        if title in existing:
            print(f"SKIP: {title} already exists")
            skipped += 1
            continue

        body = (
            "## User Story\n\n" + story +
            "\n\n## Acceptance Criteria\n\n" +
            "\n".join(f"- [ ] {item}" for item in criteria) +
            f"\n\n## Priority\n\n{priority}" +
            "\n\n## Definition of Done\n\n"
            "- [ ] Implementation completed\n"
            "- [ ] Relevant tests pass\n"
            "- [ ] Documentation updated where needed"
        )

        try:
            run_command([
                "gh", "issue", "create",
                "--repo", REPO,
                "--title", title,
                "--body", body,
                "--label", "user-story"
            ], capture=True)
            print(f"CREATED: {title}")
            created += 1
        except subprocess.CalledProcessError:
            print(f"FAILED: {title}")
            print("Create the missing label or check GitHub permissions, then rerun.")
            sys.exit(1)

    print(f"\nFinished. Created: {created}; skipped: {skipped}.")
    print("Next: add the issues to your GitHub Projects Kanban board.")


if __name__ == "__main__":
    main()
