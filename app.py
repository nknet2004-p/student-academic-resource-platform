
import streamlit as st


from database import (
    initialize_database,
    create_user,
    get_user_by_email,
    update_user_profile
)

from auth import hash_password, verify_password, register_user
from resources import (
    initialize_resource_table,
    save_resource,
    search_resources,
    get_resource_file,
    increment_downloads,
    delete_resource,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE
)

st.set_page_config(
    page_title="Student Resource Platform",
    page_icon="📚",
    layout="wide"
)

initialize_database()
initialize_resource_table()

if "user" not in st.session_state:
    st.session_state.user = None

st.title("📚 Student Academic Resource Sharing Platform")
st.caption("Share knowledge. Learn together. Succeed together.")

if st.session_state.user is None:
    register_tab, login_tab = st.tabs(["Register", "Login"])

    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input(
                "Confirm password",
                type="password"
            )
            submitted = st.form_submit_button("Create Account")

        
        if submitted:
            success, message = register_user(
                full_name,
                email,
                password,
                confirm_password
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
                key="login_password"
            )
            login_submitted = st.form_submit_button("Login")

        if login_submitted:
            user = get_user_by_email(login_email.strip().lower())

            if user and verify_password(
                login_password,
                user["password_hash"]
            ):
                st.session_state.user = {
                    "id": user["id"],
                    "name": user["full_name"],
                    "email": user["email"]
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
    ["Dashboard", "Manage Profile", "Upload Resource",
     "Browse Resources", "My Uploads"]
)

        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    if page == "Manage Profile":
        st.header("Manage Profile")

        with st.form("profile_form"):
            full_name = st.text_input(
                "Full name",
                value=user["name"]
            )
            st.text_input(
                "Email address",
                value=user["email"],
                disabled=True
            )
            submitted = st.form_submit_button("Save Changes")

        if submitted:
            try:
                updated = update_user_profile(
                    user["id"],
                    full_name
                )

                if updated:
                    st.session_state.user["name"] = full_name.strip()
                    st.success("Profile updated successfully.")
                    st.rerun()
                else:
                    st.error("Unable to update your profile.")

            except ValueError as error:
                st.error(str(error))

    if page == "Dashboard":
        st.header("Student Dashboard")
        st.write("Welcome! Your academic resources are all in one place.")

        resources = search_resources()
        my_resources = [
            item for item in resources
            if item["owner_id"] == user["id"]
        ]

        col1, col2 = st.columns(2)
        col1.metric("Available Resources", len(resources))
        col2.metric("My Uploads", len(my_resources))

    elif page == "Upload Resource":
        st.header("Upload Academic Resource")

        with st.form("upload_form", clear_on_submit=True):
            title = st.text_input("Resource title")
            description = st.text_area("Description")
            subject = st.selectbox(
                "Subject",
                ["Data Structures", "DBMS", "Operating Systems",
                 "Python", "Software Engineering", "Other"]
            )
            semester = st.selectbox(
                "Semester",
                [str(i) for i in range(1, 9)]
            )
            resource_type = st.selectbox(
                "Resource type",
                ["Notes", "Question Paper", "Assignment",
                 "Presentation", "Reference Material", "Other"]
            )
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=sorted(ext.lstrip(".") for ext in ALLOWED_EXTENSIONS)
            )
            upload_submitted = st.form_submit_button("Upload Resource")

        if upload_submitted:
            if not title.strip() or not uploaded_file:
                st.error("Title and file are required.")
            elif uploaded_file.size > MAX_FILE_SIZE:
                st.error("Maximum file size is 20 MB.")
            else:
                try:
                    save_resource(
                        user["id"], title, description, subject,
                        semester, resource_type, uploaded_file
                    )
                    st.success("Resource uploaded successfully.")
                except ValueError as error:
                    st.error(str(error))
                except Exception:
                    st.error("Upload failed. Please try again.")

    elif page == "Browse Resources":
        st.header("Browse Academic Resources")

        keyword = st.text_input("Search by title, subject, or keyword")
        col1, col2, col3 = st.columns(3)

        with col1:
            subject_filter = st.selectbox(
                "Subject",
                ["All", "Data Structures", "DBMS", "Operating Systems",
                 "Python", "Software Engineering", "Other"]
            )

        with col2:
            semester_filter = st.selectbox(
                "Semester",
                ["All"] + [str(i) for i in range(1, 9)]
            )

        with col3:
            type_filter = st.selectbox(
                "Resource type",
                ["All", "Notes", "Question Paper", "Assignment",
                 "Presentation", "Reference Material", "Other"]
            )

        results = search_resources(
            keyword, subject_filter, semester_filter, type_filter
        )

        if not results:
            st.info("No resources found. Try different search filters.")

        for resource in results:
            with st.container(border=True):
                st.subheader(resource["title"])
                st.write(resource["description"] or "No description")
                st.caption(
                    f"{resource['subject']} · Semester {resource['semester']} "
                    f"· {resource['resource_type']} · "
                    f"Uploaded by {resource['uploader']}"
                )
                st.caption(f"Downloads: {resource['downloads']}")

                file_data = get_resource_file(resource["stored_filename"])

                if file_data is not None:
                    if st.download_button(
                        "Download",
                        data=file_data,
                        file_name=resource["original_filename"],
                        key=f"download_{resource['id']}"
                    ):
                        increment_downloads(resource["id"])
                else:
                    st.warning("The resource file is missing.")

    elif page == "My Uploads":
        st.header("My Uploaded Resources")

        my_resources = [
            item for item in search_resources()
            if item["owner_id"] == user["id"]
        ]

        if not my_resources:
            st.info("You haven't uploaded any resources yet.")

        for resource in my_resources:
            with st.container(border=True):
                st.subheader(resource["title"])
                st.write(resource["description"] or "No description")
                st.caption(
                    f"{resource['subject']} · Semester {resource['semester']}"
                )

                if st.button(
                    "Delete Resource",
                    key=f"delete_{resource['id']}"
                ):
                    if delete_resource(resource["id"], user["id"]):
                        st.success("Resource deleted.")
                        st.rerun()
                    else:
                        st.error("Unable to delete this resource.")
