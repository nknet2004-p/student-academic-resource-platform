
import streamlit as st

from database import (
    initialize_database,
    get_user_by_email,
    update_user_profile,
)

from auth import verify_password, register_user

from resources import (
    initialize_resource_table,
    save_resource,
    search_resources,
    get_resource_file,
    increment_downloads,
    delete_resource,
    update_resource,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
)

st.set_page_config(
    page_title="Student Resource Platform",
    page_icon="📚",
    layout="wide",
)

initialize_database()
initialize_resource_table()

if "user" not in st.session_state:
    st.session_state.user = None

st.title("📚 Student Academic Resource Sharing Platform")
st.caption("Share knowledge. Learn together. Succeed together.")

SUBJECTS = [
    "Data Structures",
    "DBMS",
    "Operating Systems",
    "Python",
    "Software Engineering",
    "Other",
]

SEMESTERS = [str(i) for i in range(1, 9)]

RESOURCE_TYPES = [
    "Notes",
    "Question Paper",
    "Assignment",
    "Presentation",
    "Reference Material",
    "Other",
]


if st.session_state.user is None:
    register_tab, login_tab = st.tabs(["Register", "Login"])

    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
            )
            submitted = st.form_submit_button("Create Account")

        if submitted:
            success, message = register_user(
                full_name,
                email,
                password,
                confirm_password,
            )
            if success:
                st.success(message)
            else:
                st.error(message)

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )
            login_submitted = st.form_submit_button("Login")

        if login_submitted:
            user_record = get_user_by_email(
                login_email.strip().lower()
            )

            if user_record and verify_password(
                login_password,
                user_record["password_hash"],
            ):
                st.session_state.user = {
                    "id": user_record["id"],
                    "name": user_record["full_name"],
                    "email": user_record["email"],
                }
                st.rerun()
            else:
                st.error("Incorrect email or password.")

else:
    user = st.session_state.user

    with st.sidebar:
        st.write(f"Signed in as **{user['name']}**")

        page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Manage Profile",
                "Upload Resource",
                "Browse Resources",
                "My Uploads",
            ],
        )

        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    if page == "Dashboard":
        st.header("Student Dashboard")
        st.write(
            "Welcome! Your academic resources are all in one place."
        )

        all_resources = search_resources()
        my_resources = [
            resource
            for resource in all_resources
            if resource["owner_id"] == user["id"]
        ]

        col1, col2 = st.columns(2)
        col1.metric("Available Resources", len(all_resources))
        col2.metric("My Uploads", len(my_resources))

        if all_resources:
            st.subheader("Recently Shared Resources")
            for resource in all_resources[:5]:
                st.write(
                    f"**{resource['title']}** — "
                    f"{resource['subject']}, "
                    f"Semester {resource['semester']}"
                )
        else:
            st.info("No resources have been uploaded yet.")

    elif page == "Manage Profile":
        st.header("Manage Profile")

        with st.form("profile_form"):
            full_name = st.text_input(
                "Full name",
                value=user["name"],
            )
            st.text_input(
                "Email address",
                value=user["email"],
                disabled=True,
            )
            submitted = st.form_submit_button("Save Changes")

        if submitted:
            try:
                updated = update_user_profile(
                    user["id"],
                    full_name,
                )

                if updated:
                    st.session_state.user["name"] = full_name.strip()
                    st.success("Profile updated successfully.")
                    st.rerun()
                else:
                    st.error("Unable to update your profile.")

            except ValueError as error:
                st.error(str(error))

    elif page == "Upload Resource":
        st.header("Upload Academic Resource")
        st.caption("Maximum file size: 20 MB.")

        with st.form("upload_resource_form"):
            title = st.text_input("Resource title")
            description = st.text_area("Description")

            subject = st.selectbox("Subject", SUBJECTS)
            semester = st.selectbox("Semester", SEMESTERS)
            resource_type = st.selectbox(
                "Resource type",
                RESOURCE_TYPES,
            )

            uploaded_file = st.file_uploader(
                "Choose a file",
                type=[
                    extension.lstrip(".")
                    for extension in sorted(ALLOWED_EXTENSIONS)
                ],
            )

            upload_submitted = st.form_submit_button("Upload Resource")

        if upload_submitted:
            if not title.strip():
                st.error("Please enter a resource title.")
            elif uploaded_file is None:
                st.error("Please select a file to upload.")
            elif uploaded_file.size > MAX_FILE_SIZE:
                st.error("Maximum file size is 20 MB.")
            else:
                try:
                    resource_id = save_resource(
                        user["id"],
                        title,
                        description,
                        subject,
                        semester,
                        resource_type,
                        uploaded_file,
                    )
                    if resource_id:
                        st.success("Resource uploaded successfully.")
                        st.rerun()

                except ValueError as error:
                    st.error(str(error))
                except Exception as error:
                    st.error(f"Upload failed: {error}")

    elif page == "Browse Resources":
        st.header("Browse Academic Resources")
        st.write("Search and explore resources shared by students.")

        with st.container(border=True):
            keyword = st.text_input(
                "Search by title, description, or subject",
                key="browse_keyword",
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                subject_filter = st.selectbox(
                    "Filter by subject",
                    ["All"] + SUBJECTS,
                )

            with col2:
                semester_filter = st.selectbox(
                    "Filter by semester",
                    ["All"] + SEMESTERS,
                )

            with col3:
                type_filter = st.selectbox(
                    "Filter by resource type",
                    ["All"] + RESOURCE_TYPES,
                )

            sort_option = st.selectbox(
                "Sort resources by",
                [
                    "Newest First",
                    "Title A-Z",
                    "Most Downloaded",
                ],
            )

        results = search_resources(
            keyword=keyword,
            subject=subject_filter,
            semester=semester_filter,
            resource_type=type_filter,
        )

        results = list(results)

        if sort_option == "Newest First":
            results.sort(
                key=lambda item: item["id"],
                reverse=True,
            )
        elif sort_option == "Title A-Z":
            results.sort(
                key=lambda item: item["title"].lower()
            )
        elif sort_option == "Most Downloaded":
            results.sort(
                key=lambda item: item["downloads"],
                reverse=True,
            )

        st.caption(f"{len(results)} resource(s) found.")

        if not results:
            st.info(
                "No resources match your search. "
                "Try clearing the search or filters."
            )

        for resource in results:
            with st.container(border=True):
                st.subheader(resource["title"])

                st.write(
                    resource["description"] or "No description provided."
                )

                st.caption(
                    f"Subject: {resource['subject']} · "
                    f"Semester: {resource['semester']} · "
                    f"Type: {resource['resource_type']}"
                )

                st.caption(
                    f"Uploaded by {resource['uploader']} · "
                    f"Downloads: {resource['downloads']}"
                )

                file_data = get_resource_file(
                    resource["stored_filename"]
                )

                if file_data is None:
                    st.warning(
                        "The file is missing from the uploads folder."
                    )
                else:
                    st.download_button(
                        label="Download Resource",
                        data=file_data,
                        file_name=resource["original_filename"],
                        key=f"download_{resource['id']}",
                        on_click=increment_downloads,
                        args=(resource["id"],),
                    )

    elif page == "My Uploads":
        st.header("My Uploaded Resources")

        my_resources = [
            resource
            for resource in search_resources()
            if resource["owner_id"] == user["id"]
        ]

        if not my_resources:
            st.info("You haven't uploaded any resources yet.")

        for resource in my_resources:
            with st.container(border=True):
                st.subheader(resource["title"])
                st.write(
                    resource["description"] or "No description"
                )
                st.caption(
                    f"{resource['subject']} · "
                    f"Semester {resource['semester']} · "
                    f"{resource['resource_type']}"
                )

                with st.expander("Edit Resource"):
                    with st.form(f"edit_resource_{resource['id']}"):
                        edit_title = st.text_input(
                            "Resource title",
                            value=resource["title"],
                        )
                        edit_description = st.text_area(
                            "Description",
                            value=resource["description"] or "",
                        )
                        edit_subject = st.selectbox(
                            "Subject",
                            SUBJECTS,
                            index=(
                                SUBJECTS.index(resource["subject"])
                                if resource["subject"] in SUBJECTS
                                else SUBJECTS.index("Other")
                            ),
                        )
                        edit_semester = st.selectbox(
                            "Semester",
                            SEMESTERS,
                            index=(
                                SEMESTERS.index(
                                    str(resource["semester"])
                                )
                                if str(resource["semester"]) in SEMESTERS
                                else 0
                            ),
                        )
                        edit_type = st.selectbox(
                            "Resource type",
                            RESOURCE_TYPES,
                            index=(
                                RESOURCE_TYPES.index(
                                    resource["resource_type"]
                                )
                                if resource["resource_type"] in RESOURCE_TYPES
                                else RESOURCE_TYPES.index("Other")
                            ),
                        )

                        edit_submitted = st.form_submit_button(
                            "Save Changes"
                        )

                    if edit_submitted:
                        try:
                            updated = update_resource(
                                resource["id"],
                                user["id"],
                                edit_title,
                                edit_description,
                                edit_subject,
                                edit_semester,
                                edit_type,
                            )

                            if updated:
                                st.success(
                                    "Resource updated successfully."
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "Unable to update this resource."
                                )

                        except ValueError as error:
                            st.error(str(error))

                if st.button(
                    "Delete Resource",
                    key=f"delete_{resource['id']}",
                ):
                    if delete_resource(
                        resource["id"],
                        user["id"],
                    ):
                        st.success("Resource deleted.")
                        st.rerun()
                    else:
                        st.error("Unable to delete this resource.")
