import streamlit as st
import pandas as pd

from database import (
    initialize_database, get_user_by_email, update_user_profile,
    list_users, set_user_active, set_user_role, create_admin_if_configured
)
from auth import verify_password, register_user
from resources import (
    initialize_resource_table, save_resource, search_resources,
    get_resource_file, increment_downloads, delete_resource, update_resource,
    toggle_bookmark, is_bookmarked, get_bookmarks, rate_resource,
    get_user_rating, report_resource, get_resource_stats, get_admin_reports,
    update_report_status, moderate_resource, get_report_count,
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE
)

st.set_page_config(page_title="Student Resource Platform", page_icon="📚", layout="wide")
initialize_database()
initialize_resource_table()
create_admin_if_configured()

SUBJECTS = ["Data Structures", "DBMS", "Operating Systems", "Python",
            "Software Engineering", "Other"]
SEMESTERS = [str(i) for i in range(1, 9)]
RESOURCE_TYPES = ["Notes", "Question Paper", "Assignment", "Presentation",
                  "Reference Material", "Other"]

if "user" not in st.session_state:
    st.session_state.user = None

st.title("📚 Student Academic Resource Sharing Platform")
st.caption("Share knowledge. Learn together. Succeed together.")

def show_resource_card(resource, allow_edit=False):
    with st.container(border=True):
        st.subheader(resource["title"])
        st.write(resource["description"] or "No description provided.")
        st.caption(
            f"{resource['subject']} · Semester {resource['semester']} · "
            f"{resource['resource_type']} · Uploaded by {resource['uploader']}"
        )
        if "average_rating" in resource.keys():
            st.caption(
                f"⭐ {float(resource['average_rating'] or 0):.1f}/5 "
                f"({resource['rating_count']} rating(s)) · Downloads: {resource['downloads']}"
            )
        else:
            st.caption(f"Downloads: {resource['downloads']}")
        file_data = get_resource_file(resource["stored_filename"])
        if file_data is not None:
            st.download_button(
                "Download Resource", data=file_data,
                file_name=resource["original_filename"],
                key=f"download_{resource['id']}",
                on_click=increment_downloads, args=(resource["id"],)
            )
        else:
            st.warning("The uploaded file is missing from the uploads folder.")

        if st.session_state.user and resource["owner_id"] != st.session_state.user["id"]:
            uid = st.session_state.user["id"]
            bookmarked = is_bookmarked(uid, resource["id"])
            if st.button(
                "Remove Bookmark" if bookmarked else "Bookmark",
                key=f"bookmark_{resource['id']}"
            ):
                toggle_bookmark(uid, resource["id"])
                st.rerun()

            current_rating = get_user_rating(uid, resource["id"])
            rating = st.selectbox(
                "Rate this resource",
                [1, 2, 3, 4, 5],
                index=max(0, current_rating - 1),
                key=f"rating_{resource['id']}"
            )
            if st.button("Save Rating", key=f"save_rating_{resource['id']}"):
                rate_resource(uid, resource["id"], rating)
                st.success("Your rating has been saved.")
                st.rerun()

            with st.expander("Report this resource"):
                with st.form(f"report_{resource['id']}"):
                    reason = st.text_area("Reason for reporting")
                    report_submitted = st.form_submit_button("Submit Report")
                if report_submitted:
                    try:
                        report_resource(resource["id"], uid, reason)
                        st.success("Report submitted for administrator review.")
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))

if st.session_state.user is None:
    register_tab, login_tab, admin_tab = st.tabs(["Register", "Student Login", "Admin Login"])
    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account")
        if submitted:
            success, message = register_user(full_name, email, password, confirm_password)
            st.success(message) if success else st.error(message)

    with login_tab:
        with st.form("student_login_form"):
            email = st.text_input("Email", key="student_email")
            password = st.text_input("Password", type="password", key="student_password")
            submitted = st.form_submit_button("Login")
        if submitted:
            record = get_user_by_email(email.strip().lower())
            if record and verify_password(password, record["password_hash"]) and record["is_active"]:
                if record["role"] == "admin":
                    st.error("This account is an administrator. Use the Admin Login tab.")
                else:
                    st.session_state.user = {
                        "id": record["id"], "name": record["full_name"],
                        "email": record["email"], "role": record["role"]
                    }
                    st.rerun()
            else:
                st.error("Invalid credentials or account disabled.")

    with admin_tab:
        st.info("Configure ADMIN_EMAIL and ADMIN_PASSWORD before starting the app to create an administrator account.")
        with st.form("admin_login_form"):
            email = st.text_input("Administrator email", key="admin_email")
            password = st.text_input("Administrator password", type="password", key="admin_password")
            submitted = st.form_submit_button("Admin Login")
        if submitted:
            record = get_user_by_email(email.strip().lower())
            if record and record["role"] == "admin" and record["is_active"] and verify_password(password, record["password_hash"]):
                st.session_state.user = {
                    "id": record["id"], "name": record["full_name"],
                    "email": record["email"], "role": "admin"
                }
                st.rerun()
            else:
                st.error("Invalid administrator credentials.")

else:
    user = st.session_state.user
    is_admin = user.get("role") == "admin"

    with st.sidebar:
        st.write(f"Signed in as **{user['name']}**")
        if is_admin:
            st.caption("Administrator")
            pages = ["Admin Dashboard", "Manage Users", "Moderate Resources",
                     "Reports", "Browse Resources", "Manage Profile"]
        else:
            pages = ["Dashboard", "Manage Profile", "Upload Resource",
                     "Browse Resources", "My Uploads", "My Bookmarks"]
        page = st.radio("Navigation", pages)
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    if page in ("Dashboard", "Admin Dashboard"):
        st.header("Admin Dashboard" if is_admin else "Student Dashboard")
        all_resources = search_resources()
        with st.container():
            c1, c2, c3 = st.columns(3)
            c1.metric("Available Resources", len(all_resources))
            c2.metric("Total Downloads", sum(r["downloads"] for r in all_resources))
            c3.metric("Pending Reports", get_report_count() if is_admin else len(get_bookmarks(user["id"])))
        if is_admin:
            totals, popular, subjects = get_resource_stats()
            st.subheader("Platform Statistics")
            st.write(f"Registered users: {len(list_users())}")
            st.write(f"Resources: {totals['resource_count']}")
            st.write(f"Average file size: {int(totals['average_file_size'] or 0):,} bytes")
            st.subheader("Popular Resources")
            if popular:
                st.dataframe(pd.DataFrame([dict(r) for r in popular]), use_container_width=True)
            st.subheader("Resources by Subject")
            if subjects:
                st.bar_chart(pd.DataFrame([dict(r) for r in subjects]).set_index("subject"))
        else:
            st.write("Welcome! Find, save, rate, and share academic resources.")
            mine = [r for r in all_resources if r["owner_id"] == user["id"]]
            st.metric("Your Uploads", len(mine))
            st.subheader("Recently Shared Resources")
            for resource in all_resources[:5]:
                show_resource_card(resource)

    elif page == "Manage Profile":
        st.header("Manage Profile")
        with st.form("profile_form"):
            full_name = st.text_input("Full name", value=user["name"])
            st.text_input("Email address", value=user["email"], disabled=True)
            submitted = st.form_submit_button("Save Changes")
        if submitted:
            try:
                if update_user_profile(user["id"], full_name):
                    st.session_state.user["name"] = full_name.strip()
                    st.success("Profile updated.")
                    st.rerun()
                else:
                    st.error("Profile could not be updated.")
            except ValueError as error:
                st.error(str(error))

    elif page == "Upload Resource":
        st.header("Upload Academic Resource")
        st.caption("Maximum file size: 20 MB.")
        with st.form("upload_form"):
            title = st.text_input("Resource title")
            description = st.text_area("Description")
            subject = st.selectbox("Subject", SUBJECTS)
            semester = st.selectbox("Semester", SEMESTERS)
            resource_type = st.selectbox("Resource type", RESOURCE_TYPES)
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=sorted(ext.lstrip(".") for ext in ALLOWED_EXTENSIONS)
            )
            submitted = st.form_submit_button("Upload Resource")
        if submitted:
            if not title.strip():
                st.error("Resource title is required.")
            elif uploaded_file is None:
                st.error("Choose a file to upload.")
            elif uploaded_file.size > MAX_FILE_SIZE:
                st.error("Maximum file size is 20 MB.")
            else:
                try:
                    save_resource(user["id"], title, description, subject,
                                  semester, resource_type, uploaded_file)
                    st.success("Resource uploaded successfully.")
                    st.rerun()
                except (ValueError, OSError) as error:
                    st.error(str(error))

    elif page == "Browse Resources":
        st.header("Browse Academic Resources")
        with st.container(border=True):
            keyword = st.text_input("Search title, description, or subject")
            c1, c2, c3 = st.columns(3)
            with c1:
                subject = st.selectbox("Subject", ["All"] + SUBJECTS)
            with c2:
                semester = st.selectbox("Semester", ["All"] + SEMESTERS)
            with c3:
                resource_type = st.selectbox("Resource type", ["All"] + RESOURCE_TYPES)
            sort_option = st.selectbox("Sort by", ["Newest First", "Title A-Z", "Most Downloaded"])
        results = list(search_resources(keyword, subject, semester, resource_type))
        if sort_option == "Title A-Z":
            results.sort(key=lambda r: r["title"].lower())
        elif sort_option == "Most Downloaded":
            results.sort(key=lambda r: r["downloads"], reverse=True)
        else:
            results.sort(key=lambda r: r["id"], reverse=True)
        st.caption(f"{len(results)} resource(s) found.")
        if not results:
            st.info("No resources match your filters. Clear search and filters to see all resources.")
        for resource in results:
            show_resource_card(resource)

    elif page == "My Uploads":
        st.header("My Uploaded Resources")
        mine = [r for r in search_resources() if r["owner_id"] == user["id"]]
        if not mine:
            st.info("You haven't uploaded any resources yet.")
        for resource in mine:
            with st.container(border=True):
                st.subheader(resource["title"])
                st.write(resource["description"] or "No description")
                st.caption(f"{resource['subject']} · Semester {resource['semester']} · {resource['resource_type']}")
                with st.expander("Edit Resource"):
                    with st.form(f"edit_{resource['id']}"):
                        title = st.text_input("Resource title", value=resource["title"])
                        description = st.text_area("Description", value=resource["description"] or "")
                        subject = st.selectbox("Subject", SUBJECTS, index=SUBJECTS.index(resource["subject"]) if resource["subject"] in SUBJECTS else len(SUBJECTS)-1)
                        semester = st.selectbox("Semester", SEMESTERS, index=SEMESTERS.index(str(resource["semester"])) if str(resource["semester"]) in SEMESTERS else 0)
                        resource_type = st.selectbox("Resource type", RESOURCE_TYPES, index=RESOURCE_TYPES.index(resource["resource_type"]) if resource["resource_type"] in RESOURCE_TYPES else len(RESOURCE_TYPES)-1)
                        submitted = st.form_submit_button("Save Changes")
                    if submitted:
                        try:
                            if update_resource(resource["id"], user["id"], title, description, subject, semester, resource_type):
                                st.success("Resource updated.")
                                st.rerun()
                            else:
                                st.error("Unable to update resource.")
                        except ValueError as error:
                            st.error(str(error))
                if st.button("Delete Resource", key=f"delete_{resource['id']}"):
                    if delete_resource(resource["id"], user["id"]):
                        st.success("Resource deleted.")
                        st.rerun()
                    else:
                        st.error("Unable to delete resource.")

    elif page == "My Bookmarks":
        st.header("My Bookmarks")
        bookmarks = get_bookmarks(user["id"])
        if not bookmarks:
            st.info("You have not bookmarked any resources yet. Browse resources to save some.")
        for resource in bookmarks:
            show_resource_card(resource)

    elif page == "Manage Users" and is_admin:
        st.header("Manage Users")
        users = list_users()
        if users:
            st.dataframe(pd.DataFrame([dict(row) for row in users]), use_container_width=True)
            choices = {f"{row['id']} — {row['full_name']} ({row['email']})": row for row in users}
            selected_label = st.selectbox("Select a user", list(choices.keys()))
            selected = choices[selected_label]
            if selected["role"] != "admin":
                col1, col2 = st.columns(2)
                with col1:
                    if selected["is_active"] and st.button("Disable User"):
                        set_user_active(selected["id"], False)
                        st.success("User disabled.")
                        st.rerun()
                    if not selected["is_active"] and st.button("Enable User"):
                        set_user_active(selected["id"], True)
                        st.success("User enabled.")
                        st.rerun()
                with col2:
                    if st.button("Promote to Admin"):
                        set_user_role(selected["id"], "admin")
                        st.success("User promoted to administrator.")
                        st.rerun()
            else:
                st.info("Administrator account selected.")
        else:
            st.info("No users found.")

    elif page == "Moderate Resources" and is_admin:
        st.header("Moderate Resources")
        resources = list(search_resources())
        if not resources:
            st.info("No resources to moderate.")
        for resource in resources:
            with st.container(border=True):
                st.subheader(resource["title"])
                st.write(resource["description"] or "No description")
                st.caption(f"Uploader: {resource['uploader']} · {resource['subject']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve / Keep", key=f"approve_{resource['id']}"):
                        moderate_resource(resource["id"], user["id"], "approve", "Approved by administrator")
                        st.success("Resource approved.")
                        st.rerun()
                with col2:
                    if st.button("Remove Resource", key=f"remove_{resource['id']}"):
                        moderate_resource(resource["id"], user["id"], "remove", "Removed by administrator")
                        st.warning("Resource removed.")
                        st.rerun()

    elif page == "Reports" and is_admin:
        st.header("Resource Reports")
        reports = get_admin_reports()
        if not reports:
            st.info("No reports have been submitted.")
        for report in reports:
            with st.container(border=True):
                st.subheader(report["resource_title"])
                st.write(f"Reported by: {report['reporter_name']}")
                st.write(report["reason"])
                st.caption(f"Status: {report['status']} · {report['created_at']}")
                new_status = st.selectbox(
                    "Update report status",
                    ["Pending", "Reviewed", "Dismissed"],
                    index=["Pending", "Reviewed", "Dismissed"].index(report["status"]),
                    key=f"report_status_{report['id']}"
                )
                if st.button("Save Report Status", key=f"save_report_{report['id']}"):
                    update_report_status(report["id"], new_status)
                    st.success("Report status updated.")
                    st.rerun()
