import streamlit as st
from auth import (
    authenticate, get_user_role, get_all_users, add_user, 
    update_user, delete_user, change_password, init_db,
    create_session
)


def render_login_page():
    init_db()  # Ensure db and admin exist
    st.markdown("""
        <div style="padding:40px 0; text-align:center;">
            <h1 style="font-family:'Orbitron';color:#00ffcc;font-size:36px;letter-spacing:6px;margin:0;">WIDAYANKO-TERMINAL</h1>
            <p style="color:#888;font-size:14px;letter-spacing:2px;margin-top:10px;">SECURE LOGIN</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_uname", autocomplete="username")
            password = st.text_input("Password", type="password", key="login_pass", autocomplete="current-password")
            submit = st.form_submit_button("LOGIN", use_container_width=True)

            if submit:
                if authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = get_user_role(username)
                    st.session_state.app_view = "landing"
                    
                    # Create session and set query param
                    token = create_session(username)
                    st.query_params["session_token"] = token
                    
                    st.rerun()
                else:
                    st.error("Invalid username or password")

def render_profile_page():
    st.markdown("<h2 style='font-family:Orbitron;color:#00ffcc;'>User Profile</h2>", unsafe_allow_html=True)
    st.write(f"**Username:** {st.session_state.username}")
    st.write(f"**Role:** {st.session_state.role.capitalize()}")
    
    st.divider()
    st.subheader("Change Password")
    with st.form("change_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("Update Password")

        if submit:
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                success, msg = change_password(st.session_state.username, new_password)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

def render_admin_dashboard():
    if st.session_state.role != "admin":
        st.error("Access Denied. Admins only.")
        return

    st.markdown("<h2 style='font-family:Orbitron;color:#FFD700;'>Admin Dashboard</h2>", unsafe_allow_html=True)
    
    users = get_all_users()

    st.subheader("Manage Users")
    
    # Add new user
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            new_username = st.text_input("New Username", key="add_new_uname")
            new_password = st.text_input("New Password", type="password", key="add_new_pass", autocomplete="new-password")
            new_role = st.selectbox("Role", ["contributor", "admin"])
            
            # Select market access
            st.write("Permissions & Notifications")
            market_access = st.selectbox("Market Access", ["ALL", "FOREX_CRYPTO"])
            new_telegram_id = st.text_input("Telegram Chat ID (opsional)", help="Masukkan Chat ID numerik agar bot bisa mengirim sinyal ke akun Telegram ini.")

            submit_add = st.form_submit_button("Create User")
            if submit_add:
                if not new_username or not new_password:
                    st.error("Username and password are required")
                else:
                    # can_access_journal kept as True for DB-schema compatibility (journal feature removed)
                    success, msg = add_user(new_username, new_password, new_role, market_access, True, new_telegram_id)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()
    st.subheader("Existing Users")
    
    for uname, details in users.items():
        with st.expander(f"👤 {uname} ({details['role']})", expanded=False):
            with st.form(f"edit_form_{uname}"):
                edit_role = st.selectbox("Role", ["contributor", "admin"], index=0 if details['role'] == "contributor" else 1, key=f"role_{uname}")
                
                curr_market = details.get("market_access", "ALL")
                curr_journal = details.get("can_access_journal", True)  # preserved for DB compat
                curr_telegram_id = details.get("telegram_chat_id", "")

                _market_opts = ["ALL", "FOREX_CRYPTO"]
                idx_market = _market_opts.index(curr_market) if curr_market in _market_opts else 0

                edit_market = st.selectbox("Market Access", _market_opts, index=idx_market, key=f"market_{uname}")
                edit_telegram_id = st.text_input("Telegram Chat ID", value=curr_telegram_id, key=f"tg_{uname}")
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_update = st.form_submit_button("Update User")
                with col2:
                    submit_delete = st.form_submit_button("Delete User", type="primary")

                if submit_update:
                    success, msg = update_user(uname, edit_role, edit_market, curr_journal, edit_telegram_id)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
                if submit_delete:
                    if uname == st.session_state.username:
                        st.error("You cannot delete yourself.")
                    else:
                        success, msg = delete_user(uname)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                            
            # Password Change Form
            with st.form(f"pass_form_{uname}"):
                new_pass = st.text_input("New Password", type="password", key=f"newpass_{uname}")
                submit_pass = st.form_submit_button("Change Password")
                
                if submit_pass:
                    if not new_pass:
                        st.error("Password cannot be empty")
                    else:
                        from auth import change_password
                        success, msg = change_password(uname, new_pass)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
