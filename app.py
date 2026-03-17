import streamlit as st
from sidebar import sidebar
from pagess import chatbot
import sq
import os
from pathlib import Path
from PIL import Image
import datetime

st.set_page_config(page_title="AI Assistant", layout="wide")

# ---------------- SESSION STATE INIT ---------------- #
api_key = st.secrets["GROQ_API_KEY"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"


# ---------------- CUSTOM CSS (UI / COLORS ONLY) ----------------
st.markdown("""
<style>

/* ================= GLOBAL APP ================= */

.stApp{
background:
radial-gradient(900px 420px at 5% 10%, rgba(124,58,237,0.06), transparent 40%),
radial-gradient(700px 360px at 95% 90%, rgba(99,102,241,0.05), transparent 40%),
linear-gradient(180deg,#fafaff 0%,#f3f4ff 100%);
color:#0b1220;
font-family:Inter,"Segoe UI",sans-serif;
}

/* main layout */

.main .block-container{
max-width:1100px;
padding:28px 40px;
margin:auto;
}

/* ================= SIDEBAR ================= */

[data-testid="stSidebar"]{
background:linear-gradient(180deg,#ffffff 0%,#f7f6ff 100%);
border-right:1px solid rgba(124,58,237,0.08);
padding:20px;
box-shadow:4px 0 18px rgba(124,58,237,0.04);
}

/* sidebar buttons */

[data-testid="stSidebar"] .stButton>button{
width:100%;
text-align:left;
padding:11px 14px;
border-radius:10px;
background:transparent;
color:#3b2b5a;
box-shadow:none;
transition:all .15s ease;
font-weight:600;
}

[data-testid="stSidebar"] .stButton>button:hover{
background:rgba(124,58,237,0.08);
transform:translateX(2px);
}

/* ================= HEADINGS ================= */

h1{
font-weight:800;
letter-spacing:.3px;
color:#1b1335;
}

h2,h3{
font-weight:700;
color:#2b1f52;
}

/* ================= FORM CONTAINER ================= */

form{
background:white;
padding:28px;
border-radius:14px;
box-shadow:0 12px 35px rgba(124,58,237,0.06);
border:1px solid rgba(124,58,237,0.08);
}

/* ================= INPUT FIELDS ================= */

.stTextInput input{
border-radius:10px;
border:1px solid rgba(124,58,237,0.18);
padding:10px;
background:#ffffff;
font-size:14px;
transition:all .15s ease;
}

.stTextInput input:focus{
border-color:#7c4dff;
box-shadow:0 0 0 3px rgba(124,58,237,0.12);
}

/* password */

.stTextInput input[type="password"]{
letter-spacing:1px;
}

/* ================= BUTTONS ================= */

.stButton>button{
background:linear-gradient(90deg,#7c4dff,#5b21b6);
color:white;
border:none;
border-radius:10px;
padding:10px 18px;
font-weight:700;
letter-spacing:.2px;
transition:all .15s ease;
}

.stButton>button:hover{
transform:translateY(-2px);
box-shadow:0 10px 24px rgba(124,58,237,0.25);
}

/* ================= LOGIN SWITCH BUTTONS ================= */

.stButton:nth-child(1) button{
background:linear-gradient(90deg,#7c4dff,#6d28d9);
}

.stButton:nth-child(2) button{
background:linear-gradient(90deg,#6366f1,#4f46e5);
}

/* ================= SUCCESS / ERROR ================= */

.stAlert{
border-radius:10px;
font-weight:500;
}

/* ================= CHAT MESSAGES ================= */

.stChatMessage{
border-radius:12px;
padding:14px 18px;
margin-bottom:14px;
font-size:15px;
line-height:1.55;
max-width:85%;
}

/* user */

.stChatMessage[data-testid="stChatMessage-user"]{
background:linear-gradient(180deg,#f6f8ff,#eef1ff);
border:1px solid rgba(124,58,237,0.1);
box-shadow:0 6px 18px rgba(16,24,40,0.04);
margin-left:auto;
}

.stChatMessage[data-testid="stChatMessage-user"]:hover{
transform:translateY(-1px);
box-shadow:0 10px 25px rgba(124,58,237,0.08);
}

/* assistant */

.stChatMessage[data-testid="stChatMessage-assistant"]{
background:transparent;
border:none;
box-shadow:none;
margin-right:auto;
}

/* ================= CHAT INPUT ================= */

.stChatInput textarea{
border-radius:12px;
border:1px solid rgba(124,58,237,0.2);
padding:12px;
background:#ffffff;
font-size:15px;
}

.stChatInput textarea:focus{
border-color:#7c4dff;
box-shadow:0 4px 18px rgba(124,58,237,0.15);
}

/* ================= DIVIDER ================= */

hr{
border:none;
height:1px;
background:linear-gradient(90deg,transparent,#e6e2ff,transparent);
margin:25px 0;
}

/* ================= MOBILE ================= */

@media (max-width:900px){

.main .block-container{
padding-left:16px;
padding-right:16px;
}

.stChatMessage{
max-width:96%;
font-size:14px;
}

}

</style>
""", unsafe_allow_html=True)

# ---------------- HOME PAGE ---------------- #

def show():
    
    # Page config
    st.set_page_config(page_title="⚡ AI Assistant — Home", page_icon="🤖", layout="wide")

    # ---------------- API KEY (used by demo below) ----------------
    # This reads the Groq API key from Streamlit secrets. If not present, demo will show a warning.
    api_key = None
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        api_key = None

    # ---------------- CSS (professional refined theme) ----------------
    st.markdown(
        """
        <style>
        /* ================== PROFESSIONAL NEON PURPLE THEME (FINAL) ================== */

        @keyframes bgShift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .stApp {
          background:
            radial-gradient(700px 350px at 6% 12%, rgba(99,102,241,0.03), transparent 12%),
            radial-gradient(600px 300px at 92% 88%, rgba(124,58,237,0.02), transparent 12%),
            linear-gradient(180deg, #fbfbff 0%, #f7f8ff 100%);
          background-size: 180% 180%;
          animation: bgShift 30s ease infinite;
          color-scheme: light;
          font-family: Inter, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          color: #0b1220;
        }

        .main .block-container {
          max-width: 1180px;
          padding: 28px 36px;
          margin: 0 auto;
        }

        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,249,255,0.98));
          backdrop-filter: blur(4px) saturate(105%);
          border-right: 1px solid rgba(16,24,40,0.04);
          box-shadow: 0 8px 24px rgba(16,24,40,0.04);
          padding: 18px;
          border-top-left-radius: 10px;
          border-bottom-left-radius: 10px;
        }

        .css-18e3th9 h1, .css-1v3fvcr h1 {
          text-align: center;
          color: #4b0082;
          font-weight: 800;
          letter-spacing: -0.2px;
          margin-bottom: 6px;
        }
        .css-18e3th9 h1::after, .css-1v3fvcr h1::after {
          content: "";
          display: block;
          width: 56px;
          height: 4px;
          margin: 8px auto 0;
          border-radius: 4px;
          background: linear-gradient(90deg, rgba(99,102,241,0.95), rgba(124,58,237,0.95));
          opacity: 0.95;
        }

        .hero {
          display: flex;
          gap: 18px;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 28px;
        }

        .hero-left {
          flex: 1 1 52%;
        }

        .hero-right {
          flex: 1 1 44%;
          display: flex;
          gap: 12px;
          justify-content: center;
          align-items: center;
        }

        .hero-title {
          font-size: 34px;
          font-weight: 900;
          color: #2b0f4a;
          margin-bottom: 8px;
        }

        .hero-sub {
          color: #3b3b4a;
          font-size: 16px;
          margin-bottom: 18px;
        }

        .cta-row {
          display: flex;
          gap: 12px;
          align-items: center;
        }

        .feature-card {
          border-radius: 10px;
          padding: 16px;
          background: linear-gradient(180deg, #ffffff, #fbfbff);
          border: 1px solid rgba(16,24,40,0.04);
          box-shadow: 0 8px 20px rgba(16,24,40,0.03);
        }

        .gallery-grid {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 12px;
        }

        @media (max-width: 1000px) {
          .hero { flex-direction: column; }
          .hero-left, .hero-right { width: 100%; }
          .gallery-grid { grid-template-columns: repeat(2, 1fr); }
        }

        /* Sidebar chat button/icon hover fix */
        [data-testid="stSidebar"] .stButton>button svg {
          width: 18px;
          height: 18px;
          vertical-align: middle;
          fill: currentColor;
          color: rgba(75,35,160,0.78);
          transition: color 0.12s ease, transform 0.12s ease;
        }
        [data-testid="stSidebar"] .stButton>button {
          background: transparent;
          color: #3b2b5a;
          border-radius: 8px;
          padding-left: 12px;
        }
        [data-testid="stSidebar"] .stButton>button:hover {
          background: linear-gradient(90deg, rgba(99,102,241,0.06), rgba(124,58,237,0.04));
          color: #ffffff;
        }
        [data-testid="stSidebar"] .stButton>button:focus,
        [data-testid="stSidebar"] .stButton>button:active {
          background: linear-gradient(90deg, rgba(99,102,241,0.08), rgba(124,58,237,0.06));
          color: #ffffff;
          outline: none;
        }
        [data-testid="stSidebar"] .stButton>button svg [stroke] {
          stroke: currentColor;
        }
        [data-testid="stSidebar"] .stButton>button:has(svg[aria-hidden="true"]) {
          color: rgba(124,58,237,0.78);
        }
        [data-testid="stSidebar"] .stButton>button:has(svg[aria-hidden="true"]):hover {
          color: #ffffff;
        }

        /* small creative badge for demo area */
        .demo-badge {
          display:inline-block;
          padding:6px 10px;
          border-radius:999px;
          background:linear-gradient(90deg,#7c4dff,#5b21b6);
          color:white;
          font-weight:700;
          font-size:12px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------------- Layout: Hero section ----------------
    st.markdown("<div class='hero'>", unsafe_allow_html=True)

    # Left column: headline, description
    st.markdown("<div class='hero-left'>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title'>⚡ AI Assistant — Fast, Accurate, Professional</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero-sub'>A powerful AI assistant built for developers, learners, and creators. "
        "Streamlined workflows, voice input, TTS, code help, and a clean, professional UI — all in one place.</div>",
        unsafe_allow_html=True,
    )

    # Remove the top three CTA buttons as requested (no Start / History / Demo here)
    st.markdown("</div>", unsafe_allow_html=True)  # close hero-left

    # Right column: stacked hero images (two images side by side)
    st.markdown("<div class='hero-right'>", unsafe_allow_html=True)
    img_folder = Path("img")
    hero_imgs = ["hero_1.jpg", "hero_2.jpg"]
    for fname in hero_imgs:
        p = img_folder / fname
        if p.exists():
            try:
                im = Image.open(p)
                # Use explicit width for hero thumbnails; avoid deprecated use_column_width
                st.image(im, width=320)
            except Exception:
                st.empty()
        else:
            st.empty()
    st.markdown("</div>", unsafe_allow_html=True)  # close hero-right
    st.markdown("</div>", unsafe_allow_html=True)  # close hero

    st.divider()

    # ---------------- Features section ----------------
    st.markdown("### What this assistant does")
    fcol1, fcol2, fcol3 = st.columns(3)
    features = [
        ("Fast Answers", "High-speed streaming responses with concise results.", "feature_1.jpg"),
        ("Voice Input & TTS", "Speak in and listen to responses with natural voices.", "feature_2.jpg"),
        ("Code & Debug", "Get code samples, explanations, and debugging help.", "feature_3.jpg"),
    ]
    for col, (title, desc, fname) in zip((fcol1, fcol2, fcol3), features):
        with col:
            st.markdown(f"<div class='feature-card'><h4 style='margin:0 0 8px 0'>{title}</h4>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:#4b4b5b;margin-bottom:10px'>{desc}</div>", unsafe_allow_html=True)
            p = img_folder / fname
            if p.exists():
                try:
                    im = Image.open(p)
                    # use_container_width replaces deprecated use_column_width
                    st.image(im, use_container_width=True)
                except Exception:
                    st.write("")  # keep layout
            else:
                st.write("")  # keep layout
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ---------------- Gallery / Showcase (5 images) ----------------
    st.markdown("### Gallery — snapshots")
    gallery_files = ["gallery_1.jpg", "gallery_2.jpg", "gallery_3.jpg", "gallery_4.jpg", "gallery_5.jpg"]
    cols = st.columns(5)
    for i, fname in enumerate(gallery_files):
        p = img_folder / fname
        with cols[i % 5]:
            if p.exists():
                try:
                    im = Image.open(p)
                    st.image(im, caption=fname.replace(".jpg", "").replace("_", " ").title(), use_container_width=True)
                except Exception:
                    st.write("")  # placeholder
            else:
                st.write("")  # placeholder

    st.divider()

    # ---------------- Quick demo area (real API call) ----------------
    
    st.markdown("### Quick demo  <span class='demo-badge'>Live</span>", unsafe_allow_html=True)
    st.markdown(
    "Type your prompt below and click **Send** to interact with the AI Assistant. "
    "Ask questions, explore ideas, or get instant help with tasks while the assistant generates accurate responses in real time."
)

    demo_col1, demo_col2 = st.columns([4, 1])
    with demo_col1:
        sample = st.text_input(
            "Enter prompt to send to the model:",
            value="Explain Python list comprehensions in simple terms. Give an example. Keep it short."
        )
    with demo_col2:
        send = st.button("Send")

    # Token control (default 50 as requested)
    max_tokens = st.number_input(
        "Max tokens (demo)",
        min_value=10,
        max_value=1024,
        value=50,
        step=10,
        help="Token limit for the demo response"
    )

    # Display area for preview, response and token usage
    preview_area = st.empty()
    response_area = st.empty()
    meta_area = st.empty()

    def truncate_to_nth_fullstop(text: str, n: int = 2) -> str:
        """
        Return text up to the nth full stop ('.') inclusive.
        If fewer than n full stops exist, return up to the last full stop found.
        If no full stop exists, return the whole text (trimmed).
        """
        if not text:
            return ""
        t = " ".join(text.strip().split())
        idx = -1
        count = 0
        for i, ch in enumerate(t):
            if ch == ".":
                count += 1
                idx = i
                if count == n:
                    break
        if idx != -1:
            return t[: idx + 1].strip()
        return t.strip()

    # When user clicks Send:
    if send:
        # 1) Show truncated preview of the user's prompt (up to 2nd full stop)
        preview_text = truncate_to_nth_fullstop(sample, n=2)
        if not preview_text:
            preview_text = sample.strip() or "(empty prompt)"
        

        # 2) Validate API key
        if not api_key:
            st.error("Groq API key not found in st.secrets['GROQ_API_KEY']. Please add it to run the demo.")
        else:
            # Lazy import to avoid errors if Groq not installed until demo is used
            try:
                from groq import Groq
            except Exception:
                st.error("Groq SDK not available in the environment. Install the 'groq' package to run the demo.")
                st.stop()

            try:
                client = Groq(api_key=api_key)
            except Exception:
                st.error("Failed to initialize Groq client. Check your API key and environment.")
                st.stop()

            model = "llama-3.1-8b-instant"
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Keep answers concise."},
                {"role": "user", "content": sample}
            ]

            # 3) Call the API (non-streaming) and show only the truncated assistant reply
            try:
                with st.spinner("Generating concise response..."):
                    resp = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=int(max_tokens),
                        temperature=0.2,
                        stream=False
                    )

                    # Extract text safely (robust to SDK variations)
                    full_response = ""
                    try:
                        if hasattr(resp, "choices") and resp.choices:
                            choice = resp.choices[0]
                            if getattr(choice, "message", None) and getattr(choice.message, "content", None):
                                full_response = choice.message.content
                            elif getattr(choice, "text", None):
                                full_response = choice.text
                            else:
                                full_response = str(choice)
                        else:
                            full_response = str(resp)
                    except Exception:
                        full_response = str(resp)

                    # 4) Truncate assistant response to second full stop for concise display
                    truncated_response = truncate_to_nth_fullstop(full_response, n=2)
                    if not truncated_response:
                        truncated_response = full_response.strip() or "(no response)"

                    # 5) Nicely styled UI card showing only the concise reply (no full response)
                    st.warning(f"**Assistant (concise):** {truncated_response}")

                    # 6) Token usage: try to extract usage info if present
                    usage_text = "Token usage: not available"
                    try:
                        if hasattr(resp, "usage"):
                            u = resp.usage
                            total = getattr(u, "total_tokens", None) or (u.get("total_tokens") if isinstance(u, dict) else None)
                            prompt_t = getattr(u, "prompt_tokens", None) or (u.get("prompt_tokens") if isinstance(u, dict) else None)
                            comp_t = getattr(u, "completion_tokens", None) or (u.get("completion_tokens") if isinstance(u, dict) else None)
                            parts = []
                            if prompt_t is not None:
                                parts.append(f"prompt: {prompt_t}")
                            if comp_t is not None:
                                parts.append(f"completion: {comp_t}")
                            if total is not None:
                                parts.append(f"total: {total}")
                            if parts:
                                usage_text = "Token usage: " + ", ".join(parts)
                        else:
                            usage_text = f"Requested max tokens: {max_tokens}"
                    except Exception:
                        usage_text = f"Requested max tokens: {max_tokens}"

                    # 7) Show metadata: model, timestamp, usage
                    import datetime as _dt
                    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    

                    # 8) Save concise result in session (keeps full_response but does not display it)
                    st.session_state["home_demo_last"] = {
                        "prompt": sample,
                        "preview_sent": preview_text,
                        "response_full": full_response,
                        "response_preview": truncated_response,
                        "usage": usage_text,
                        "model": model,
                        "timestamp": ts
                    }

            except Exception as e:
                st.error(f"API request failed: {e}")

    # ---------------- Footer with credits and image file reminder ----------------
    st.markdown(
    """
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div style="color:#5b5b6b">
        <strong>AI Assistant</strong> — Your intelligent workspace for conversations, insights, and productivity. 
        Use the sidebar to manage settings, explore features, and access your chat history.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

    st.markdown("---")
 

# ---------------- LOGIN PAGE ---------------- #
def show_login():

    st.markdown("## 🔐 Account Access")
    st.write("Login to access the **AI Assistant Chatbot**.")

    # ---- session defaults ----
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login", key="switch_login", use_container_width=True):
            st.session_state.auth_mode = "login"

    with col2:
        if st.button("Create Account", key="switch_signup", use_container_width=True):
            st.session_state.auth_mode = "signup"

    st.divider()

    # ---------------- LOGIN FORM ---------------- #

    if st.session_state.auth_mode == "login":

        st.subheader("Login to your account")

        with st.form("login_form", clear_on_submit=False):

            username = st.text_input("Username", key="login_user").strip().lower()
            password = st.text_input("Password", type="password", key="login_pass")

            submit_login = st.form_submit_button("Login Now")

            if submit_login:

                if username == "" or password == "":
                    st.warning("Please fill all fields")
                    return

                with st.spinner("Authenticating..."):

                    if sq.login_user(username, password):

                        st.session_state.logged_in = True
                        st.session_state.current_user = username
                        st.session_state.messages = []
                        st.session_state.last_prompt = None
                        st.session_state.voice_prompt = None

                        st.success(f"Welcome {username} 👋")

                        st.rerun()

                    else:
                        st.error("Invalid username or password")


    # ---------------- SIGNUP FORM ---------------- #

    if st.session_state.auth_mode == "signup":

        st.subheader("Create New Account")

        with st.form("signup_form", clear_on_submit=False):

            new_user = st.text_input("Choose Username", key="signup_user").strip().lower()
            new_pass = st.text_input("Create Password", type="password", key="signup_pass").strip()
            confirm_pass = st.text_input("Confirm Password", type="password").strip()

            submit_signup = st.form_submit_button("Create Account")

            if submit_signup:

                if new_user == "" or new_pass == "" or confirm_pass == "":
                    st.warning("All fields are required")
                    return

                if len(new_user) < 3:
                    st.warning("Username must be at least 3 characters")
                    return

                if sq.user_exists(new_user):
                    st.warning("Username already exists")
                    return

                if new_pass != confirm_pass:
                    st.warning("Passwords do not match")
                    return

                if len(new_pass) < 4:
                    st.warning("Password must be at least 4 characters")
                    return

                with st.spinner("Creating your account..."):

                    sq.create_user(new_user, new_pass)

                    # 🔹 create user chat folder
                    user_folder = os.path.join("chat_history", new_user)

                    try:
                        os.makedirs(user_folder, exist_ok=True)
                    except Exception as e:
                        st.error(f"Folder creation error: {e}")
                        return

                st.success("Account created successfully 🎉")
                st.info("You can now login")

                st.session_state.auth_mode = "login"

                st.rerun()

@st.dialog("Confirm Logout")
def confirm_logout():

    st.write("⚠️ Are you sure you want to logout?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Yes Logout"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.messages = []
            st.session_state.last_prompt = None
            st.session_state.voice_prompt = None
            st.success("Logged out successfully")
            st.rerun()

    with col2:
        if st.button("Cancel"):
            st.rerun()




# ---------------- NAVIGATION ---------------- #

page = sidebar()

if page == "Home":
    show()

elif page == "Chatbot":
    chatbot.check_login_and_run(st.session_state)

elif page=='Login':
    show_login()

elif page=='Logout':
     confirm_logout()