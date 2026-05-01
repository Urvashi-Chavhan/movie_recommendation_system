# auth.py

import bcrypt
import streamlit as st
from database import user_exists, add_user, get_user

# ── Hash Password ─────────────────────────────────────────
def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

# ── Verify Password ───────────────────────────────────────
def verify_password(password, hashed):
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8")
    )

# ── Signup Page ───────────────────────────────────────────
def show_signup():
    st.title("🎬 Movie App — Create Account")
    st.markdown("---")

    with st.container():
        st.subheader("📝 Sign Up")

        email    = st.text_input("📧 Email")
        username = st.text_input("👤 Username")
        password = st.text_input("🔒 Password", type="password")
        confirm  = st.text_input("🔒 Confirm Password", type="password")

        if st.button("Create Account", use_container_width=True):

            # Validations
            if not email or not username or not password:
                st.error("⚠️ All fields are required!")

            elif len(username) < 3:
                st.error("⚠️ Username must be at least 3 characters!")

            elif len(password) < 6:
                st.error("⚠️ Password must be at least 6 characters!")

            elif password != confirm:
                st.error("⚠️ Passwords do not match!")

            elif user_exists(username):
                st.error("⚠️ Username already taken. Try another!")

            else:
                hashed = hash_password(password)
                add_user(username, hashed, email)
                st.success("✅ Account created! Please login now.")
                st.session_state.page = "login"
                st.rerun()

        st.markdown("---")
        st.markdown("Already have an account?")
        if st.button("Go to Login →", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

# ── Login Page ────────────────────────────────────────────
def show_login():
    st.title("🎬 Movie Recommendation App")
    st.markdown("---")

    with st.container():
        st.subheader("🔐 Login")

        username = st.text_input("👤 Username")
        password = st.text_input("🔒 Password", type="password")

        if st.button("Login", use_container_width=True):

            if not username or not password:
                st.error("⚠️ Please enter username and password!")

            else:
                user = get_user(username)

                if user is None:
                    st.error("❌ Username not found!")

                elif not verify_password(password, user["password"]):
                    st.error("❌ Incorrect password!")

                else:
                    # ✅ Login success
                    st.session_state.logged_in = True
                    st.session_state.username  = username
                    st.session_state.page      = "home"
                    st.success(f"✅ Welcome back, {username}!")
                    st.rerun()

        st.markdown("---")
        st.markdown("Don't have an account?")
        if st.button("Create Account →", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()