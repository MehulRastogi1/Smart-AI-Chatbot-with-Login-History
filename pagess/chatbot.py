
def show_with_login(session_state):
    import random
    import streamlit as st
    from groq import Groq
    from ddgs import DDGS
    import pandas as pd
    import speech_recognition as sr
    from deep_translator import GoogleTranslator
    import edge_tts
    import asyncio
    import base64
    from streamlit_mic_recorder import mic_recorder
    import tempfile

    # New imports for chat history
    import os
    import glob
    import datetime
    import re
    import string
    import shutil

    # ---------------- PAGE CONFIG ----------------
    st.set_page_config(
        page_title="AI Chat Assistant",
        page_icon="🤖",
        layout="wide"
    )

    # ---------------- CHAT HISTORY HELPERS ----------------
    username = session_state.get("current_user")
    CHAT_HISTORY_DIR = os.path.join("chat_history", username)

    def ensure_history_folder():
        try:
            os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
        except Exception:
            try:
                st.sidebar.warning("Could not create chat_history folder. History will be disabled.")
            except Exception:
                pass

    def list_chat_files():
        """
        FIX: Read all .txt files in chat_history (not only chat_*.txt).
        Returns a list of full paths sorted by modification time (oldest first).
        """
        ensure_history_folder()
        try:
            pattern = os.path.join(CHAT_HISTORY_DIR, "*.txt")  # include all txt files
            files = glob.glob(pattern)
            # Filter only files (ignore directories) and ensure readable paths
            files = [f for f in files if os.path.isfile(f)]
            # Sort by modification time ascending (oldest first)
            files_sorted = sorted(files, key=lambda p: os.path.getmtime(p))
            return files_sorted
        except Exception:
            # On any error, return empty list (safe fallback)
            return []


    def create_new_chat_file():
        """
        Create a timestamped chat file and return its path.
        Note: We will not call this on startup; only when first user prompt arrives.
        """
        ensure_history_folder()
        ts = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        filename = f"chat_{ts}.txt"
        path = os.path.join(CHAT_HISTORY_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            try:
                st.sidebar.error("Failed to create new chat file.")
            except Exception:
                pass
            return None
        return path

    def safe_read_file(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def safe_write_file(path, text, mode="a"):
        try:
            with open(path, mode, encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception:
            try:
                st.sidebar.error(f"Failed to write to {os.path.basename(path)}.")
            except Exception:
                pass
            return False

    def slugify_text(text):
        try:
            text = re.sub(r"\s+", " ", text.strip())
            translator = str.maketrans("", "", string.punctuation)
            cleaned = text.translate(translator)
            cleaned = cleaned.lower()
            words = cleaned.split()
            words = words[:6]
            slug = "_".join(words)
            if len(slug) > 50:
                slug = slug[:50].rstrip("_")
            slug = slug.strip("_")
            if not slug:
                slug = "chat"
            return slug
        except Exception:
            return "chat"

    def generate_filename_from_prompt(prompt, original_path):
        """
        Generate a safe filename based on prompt and ensure no duplicates.
        Returns new full path or None on failure.
        """
        try:
            base = slugify_text(prompt)
            candidate = f"{base}.txt"
            candidate_path = os.path.join(CHAT_HISTORY_DIR, candidate)
            if not os.path.exists(candidate_path):
                return candidate_path
            idx = 2
            while True:
                candidate = f"{base}_{idx}.txt"
                candidate_path = os.path.join(CHAT_HISTORY_DIR, candidate)
                if not os.path.exists(candidate_path):
                    return candidate_path
                idx += 1
                if idx > 9999:
                    break
            return None
        except Exception:
            return None

    def display_name_from_filename(path):
        try:
            fname = os.path.basename(path)
            name = fname.replace(".txt", "")
            if name.startswith("chat_"):
                name_body = name[5:]
                pretty = name_body.replace("_", " ")
                pretty = pretty.replace("-", " ").replace("_", " ")
                pretty = re.sub(r"\s+", " ", pretty).strip()
                return pretty
            else:
                pretty = name.replace("_", " ")
                pretty = re.sub(r"\s+", " ", pretty).strip()
                return pretty
        except Exception:
            return os.path.basename(path)

    def safe_delete_file(path):
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            try:
                shutil.rmtree(path)
                return True
            except Exception:
                try:
                    st.sidebar.error(f"Failed to delete {os.path.basename(path)}.")
                except Exception:
                    pass
                return False

    def parse_chat_file(path):
        """
        FIX: Robustly parse a chat file with blocks:
        USER:
        <text>

        ASSISTANT:
        <text>

        Returns:
        [
            {"role":"user","content":"..."},
            {"role":"assistant","content":"..."},
            ...
        ]

        Safe on missing file or malformed content.
        """
        messages = []
        if not path or not os.path.exists(path):
            return messages

        try:
            content = safe_read_file(path)
        except Exception:
            return messages

        # Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Regex finds USER: or ASSISTANT: followed by any text until next tag or EOF
        pattern = r"(USER:|ASSISTANT:)\n(.*?)(?=(?:\n(?:USER:|ASSISTANT:)\n)|\Z)"
        try:
            matches = re.findall(pattern, content, flags=re.S)
        except Exception:
            matches = []

        for tag, body in matches:
            text = body.strip()
            if not text:
                continue
            if tag == "USER:":
                messages.append({"role": "user", "content": text})
            elif tag == "ASSISTANT:":
                messages.append({"role": "assistant", "content": text})

        return messages

    # ---------------- FUNCTION ----------------
    # ------------------- VOICE INPUT FUNCTION -------------------
    def voice_input_to_prompt(audio):

        temp_path = None

        try:
            raw = audio.get("bytes")

            # agar bytes base64 me aaye
            if isinstance(raw, str):
                raw = base64.b64decode(raw)

            # temp file create
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
            temp_path = tf.name
            tf.write(raw)
            tf.close()

            # Groq Whisper STT
            transcription = client.audio.transcriptions.create(
                file=(temp_path, open(temp_path, "rb").read()),
                model="whisper-large-v3",
                response_format="json",
                language="hi"
            )

            text = transcription.text

            translated = GoogleTranslator(
                source="auto",
                target="en"
            ).translate(text)

            st.success(f"🗣 You said: {text}")
            st.info(f"🌍 English: {translated}")

            st.session_state.voice_prompt = translated
            return translated

        except Exception as e:
            st.error(f"⚠️ Error: {e}")
            return None

    # -------- WEB SEARCH --------
    def search_web(query, results=5):

        output = []

        try:
            with DDGS() as ddgs:

                for r in ddgs.text(query, max_results=results):

                    title = r["title"]
                    body = r["body"]
                    link = r["href"]

                    output.append(f"{title}\n{body}\n{link}")

        except:
            return "Web search failed."

        return "\n\n".join(output)

    # ---------------- SESSION STATE ----------------
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_prompt" not in st.session_state:
        st.session_state.last_prompt = None

    if "regen" not in st.session_state:
        st.session_state.regen = False

    if "voice_prompt" not in st.session_state:
        st.session_state.voice_prompt = None
        st.session_state.last_response = None

    if "voice" not in st.session_state:
        st.session_state.voice = False

    # Chat history session vars
    if "current_chat_file" not in st.session_state:
        # IMPORTANT: start with None; do NOT create a file on startup
        st.session_state.current_chat_file = None

    if "available_chats" not in st.session_state:
        st.session_state.available_chats = list_chat_files()

    # For delete confirmation flow
    if "to_delete" not in st.session_state:
        st.session_state.to_delete = None

    # ---------------- CUSTOM CSS (UI / COLORS ONLY) ----------------
    st.markdown("""
<style>

/* ================= PREMIUM PURPLE UI ================= */

/* Background */
.stApp{
background:
radial-gradient(900px 420px at 5% 10%, rgba(124,58,237,0.05), transparent 15%),
radial-gradient(700px 360px at 95% 90%, rgba(99,102,241,0.04), transparent 15%),
linear-gradient(180deg,#fafaff 0%,#f3f4ff 100%);
color:#0b1220;
font-family:Inter,"Segoe UI",sans-serif;
}

/* Layout */
.main .block-container{
max-width:1180px;
padding:22px 34px;
margin:auto;
}

/* ================= SIDEBAR ================= */

[data-testid="stSidebar"]{
background:linear-gradient(180deg,#ffffff 0%,#f7f6ff 100%);
border-right:1px solid rgba(124,58,237,0.08);
padding:18px;
box-shadow:4px 0 18px rgba(124,58,237,0.04);
}

/* Sidebar headings */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label{
color:#3b2b5a;
font-weight:700;
letter-spacing:0.2px;
}

/* Sidebar chat list */

[data-testid="stSidebar"] .stButton>button{
width:100%;
text-align:left;
padding:10px 12px;
border-radius:8px;
background:transparent;
color:#3b2b5a;
box-shadow:none;
transition:all .12s ease;
}

/* sidebar hover */

[data-testid="stSidebar"] .stButton>button:hover{
background:rgba(124,58,237,0.07);
}

/* Sidebar icons */

[data-testid="stSidebar"] .stButton>button svg{
width:16px;
height:16px;
color:#7c4dff;
opacity:.85;
transition:opacity .1s ease;
}

[data-testid="stSidebar"] .stButton>button:hover svg{
opacity:1;
}

/* delete icon */

[data-testid="stSidebar"] .stButton>button:has(svg[aria-hidden="true"]){
color:#7c4dff;
}

[data-testid="stSidebar"] .stButton>button:has(svg[aria-hidden="true"]):hover{
color:#e11d48;
}

/* ================= CHAT MESSAGES ================= */

/* Base */

.stChatMessage{
border-radius:10px;
padding:14px 18px;
margin-bottom:14px;
font-size:15px;
line-height:1.55;
max-width:86%;
}

/* USER MESSAGE */

.stChatMessage[data-testid="stChatMessage-user"]{
background:linear-gradient(180deg,#f6f8ff,#eef1ff);
border:1px solid rgba(124,58,237,0.08);
box-shadow:0 6px 18px rgba(16,24,40,0.04);
margin-left:auto;
transition:all .12s ease;
}

/* user hover */

.stChatMessage[data-testid="stChatMessage-user"]:hover{
transform:translateY(-1px);
box-shadow:0 8px 22px rgba(124,58,237,0.08);
background:linear-gradient(180deg,#f3f6ff,#e9edff);
}

/* ASSISTANT RESPONSE */

.stChatMessage[data-testid="stChatMessage-assistant"]{
background:transparent;
border:none;
box-shadow:none;
margin-right:auto;
padding-left:4px;
}

/* remove hover */

.stChatMessage[data-testid="stChatMessage-assistant"]:hover{
background:transparent;
box-shadow:none;
transform:none;
}

/* ================= CHAT INPUT ================= */

.stChatInput textarea{
border-radius:10px;
border:1px solid rgba(124,58,237,0.15);
padding:12px;
background:#ffffff;
font-size:15px;
}

.stChatInput textarea:focus{
border-color:#7c4dff;
box-shadow:0 4px 18px rgba(124,58,237,0.12);
}

/* ================= BUTTONS ================= */

.stButton>button{
background:linear-gradient(90deg,#7c4dff,#5b21b6);
color:white;
border:none;
border-radius:10px;
padding:10px 16px;
font-weight:700;
transition:all .12s ease;
}

.stButton>button:hover{
transform:translateY(-1px);
box-shadow:0 8px 22px rgba(124,58,237,0.18);
}

/* ================= ACCESSIBILITY ================= */

:focus{
outline:2px solid rgba(124,58,237,0.15);
outline-offset:2px;
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

    # ---------------- API KEY ----------------
    api_key = st.secrets["GROQ_API_KEY"]

    client = None
    if api_key:
        client = Groq(api_key=api_key)

    # ---------------- SIDEBAR ----------------
    
    # ---------------- Chat History Sidebar Display and Chat Loading ----------------
    st.sidebar.title("💬 Chat History")

    # Refresh available chats list (use the corrected list_chat_files)
    st.session_state.available_chats = list_chat_files()

    # New Chat button (keeps behavior: no file created until first user prompt)
    if st.sidebar.button("➕ New Chat"):
        st.session_state.current_chat_file = None
        st.session_state.messages = []
        st.session_state.last_prompt = None
        st.session_state.last_response = None
        st.session_state.to_delete = None
        st.session_state.available_chats = list_chat_files()
        st.rerun()

    # Display all .txt chat files in the sidebar with readable names and delete icon
    if st.session_state.available_chats:
        # Show newest first for convenience
        for path in reversed(st.session_state.available_chats):
            fname = os.path.basename(path)
            display_name = display_name_from_filename(path)

            # Two-column layout: chat name (clickable) and delete button
            col_a, col_b = st.sidebar.columns([8, 1])

            # When user clicks the chat name, load and parse the file, update session state
            if col_a.button(display_name, key=f"chat_btn_{fname}"):
                parsed = parse_chat_file(path)  # use corrected parser
                # Update session state with parsed messages and current file
                st.session_state.messages = parsed
                st.session_state.current_chat_file = path
                # Update last_prompt and last_response from parsed messages (if present)
                last_user = None
                last_assistant = None
                for m in reversed(parsed):
                    if last_assistant is None and m["role"] == "assistant":
                        last_assistant = m["content"]
                    if last_user is None and m["role"] == "user":
                        last_user = m["content"]
                    if last_user is not None and last_assistant is not None:
                        break
                st.session_state.last_prompt = last_user
                st.session_state.last_response = last_assistant
                st.session_state.to_delete = None
                # Rerun to display messages in main chat area
                st.rerun()

            # Delete icon next to each chat (existing delete flow will handle confirmation)
            if col_b.button("🗑", key=f"del_btn_{fname}"):
                st.session_state.to_delete = path
                st.rerun()
    else:
        st.sidebar.info("No chats yet. Click ➕ New Chat to start.")

   
    # If a delete was requested, show confirmation
    if st.session_state.to_delete:
        try:
            st.sidebar.markdown("---")
            st.sidebar.warning(f"Are you sure you want to delete **{display_name_from_filename(st.session_state.to_delete)}**?")
            c_yes, c_no = st.sidebar.columns([1, 1])
            if c_yes.button("Yes Delete", key="confirm_delete_yes"):
                deleted = safe_delete_file(st.session_state.to_delete)
                st.session_state.available_chats = list_chat_files()
                if deleted and st.session_state.current_chat_file == st.session_state.to_delete:
                    st.session_state.current_chat_file = None
                    st.session_state.messages = []
                    st.session_state.last_prompt = None
                    st.session_state.last_response = None
                st.session_state.to_delete = None
                st.rerun()
            if c_no.button("Cancel", key="confirm_delete_no"):
                st.session_state.to_delete = None
                st.rerun()
        except Exception:
            st.session_state.to_delete = None

    st.sidebar.markdown("---")
    st.sidebar.title("⚙️ AI Settings")
    mode = st.sidebar.radio(
        "Select AI Mode",
        ["FAST", "THINK HARD", "CODER"]
    )

    # ---------------- AI SETTINGS ----------------
    
    with st.sidebar.expander("⚙️ Model Settings", expanded=True):

        mode_configs = {
            "FAST": {
                "model": "llama-3.1-8b-instant",
                "temperature": 0.3,
                "max_tokens": 300,
                "system_prompt": "Give short and direct answers."
            },

            "THINK HARD": {
                "model": "qwen/qwen3-32b",
                "temperature": 0.2,
                "max_tokens": 1500,
                "system_prompt": "Think step by step and solve complex problems."
            },
            "CODER": {
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.2,
                "max_tokens": 1200,
                "system_prompt": "You are an expert programmer. Write clean, correct and optimized code."
            }
        }

        config = mode_configs[mode]

        model = st.selectbox(
            "Model",
            [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "qwen/qwen3-32b"
            ],
            index=0 if config["model"] == "llama-3.1-8b-instant"
            else 1 if config["model"] == "llama-3.3-70b-versatile"
            else 2 if config["model"] == "qwen/qwen3-32b"
            else 3
        )

        max_tokens = st.slider(
            "Max Tokens",
            100,
            4096,
            config["max_tokens"]
        )

    temperature = config["temperature"]
    web_mode = st.sidebar.toggle("🌐 Internet Access")

    # -------- FILE UPLOAD --------
    uploaded_file = st.sidebar.file_uploader(
        "📂 Upload file (CSV / TXT)",
        type=["csv", "txt"]
    )

    file_text = ""

    if uploaded_file:
        try:
            if uploaded_file.type == "text/csv":
                df = pd.read_csv(uploaded_file)
                file_text = df.to_string()
            elif uploaded_file.type == "text/plain":
                file_text = uploaded_file.read().decode("utf-8")
        except:
            file_text = "Failed to read file."

    # ---------------- VOICE SETTINGS ----------------
    if "voice_settings" not in st.session_state:
        st.session_state.voice_settings = {
            "rate": "Normal",
            "volume": 1.0,
            "voice": None
        }
        st.session_state.last_response = None

    with st.sidebar.expander("🔊 Voice Settings"):
        rate_choice = st.selectbox(
            "Speech Rate",
            ["Normal", "High", "Slow"]
        )
        st.session_state.voice_settings["rate"] = rate_choice
        voice_choice = st.selectbox(
            "Voice",
            [
                "Default",
                "English Male",
                "English Female",
                "Hindi Female"
            ]
        )
        st.session_state.voice_settings["voice"] = voice_choice

    st.sidebar.markdown("---")

    # ------------------- SIDEBAR BUTTONS SIDE BY SIDE -------------------
    col1, col2 = st.sidebar.columns([1, 1])

    # -------- Clear Chat Button --------
    with col1:
        if st.button("🗑 Clear Chat"):
            st.session_state.messages = []
            st.session_state.last_prompt = None
            st.session_state.voice_prompt = None
            # reset current chat (do not create file)
            st.session_state.current_chat_file = None
            st.session_state.available_chats = list_chat_files()
            st.rerun()

    with col2:
        audio = mic_recorder(
            start_prompt="🎤 Start recording",
            stop_prompt="⏹ Stop recording",
            just_once=True
        )

        if audio:
            result = voice_input_to_prompt(audio)
            if result:
                st.session_state.voice = True
                st.rerun()

    # ---------------- TITLE ----------------
    st.title("🤖 AI Chat Assistant")

    # ---------------- DISPLAY HISTORY ----------------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ---------------- USER INPUT ----------------
    prompt = st.chat_input("Ask anything...")

    # ---------- Helper functions for writing messages (fixed) ----------
    def append_user_to_file(path, user_text):
        """
        Create file on first user prompt, append user message,
        rename file based on first prompt and update session_state.current_chat_file.
        """
        try:
            # Prefer session state's current file if present
            current_path = st.session_state.get("current_chat_file") or path

            # If no file exists yet, create it now (only at first user prompt)
            if not current_path:
                current_path = create_new_chat_file()
                st.session_state.current_chat_file = current_path
                st.session_state.available_chats = list_chat_files()

            # Ensure file exists
            if not os.path.exists(current_path):
                safe_write_file(current_path, "")

            # Check if file was empty before writing (first user message)
            current_content = safe_read_file(current_path)
            is_first_user = (current_content.strip() == "")

            # Append the user message
            to_write = "USER:\n" + user_text.strip() + "\n\n"
            safe_write_file(current_path, to_write, mode="a")

            # If this was the first user message, attempt to rename the file based on the prompt
            if is_first_user:
                try:
                    new_path = generate_filename_from_prompt(user_text, current_path)
                    if new_path and new_path != current_path:
                        try:
                            os.replace(current_path, new_path)
                        except Exception:
                            try:
                                shutil.move(current_path, new_path)
                            except Exception:
                                new_path = None
                        if new_path:
                            # CRITICAL: update session state to the new path so future writes go to it
                            st.session_state.current_chat_file = new_path
                            st.session_state.available_chats = list_chat_files()
                            current_path = new_path
                except Exception:
                    pass

            # Ensure session state always points to the file we just wrote to
            st.session_state.current_chat_file = current_path

            return current_path

        except Exception as e:
            try:
                st.sidebar.error(f"Failed to write user message to history: {e}")
            except Exception:
                pass
            return path

    def append_assistant_to_file(path, assistant_text):
        """
        Append assistant response to the current chat file (uses session_state.current_chat_file).
        """
        try:
            current_path = st.session_state.get("current_chat_file") or path

            # Defensive: if still None, create a new chat file (shouldn't normally happen)
            if not current_path:
                current_path = create_new_chat_file()
                st.session_state.current_chat_file = current_path
                st.session_state.available_chats = list_chat_files()

            if not os.path.exists(current_path):
                safe_write_file(current_path, "")

            to_write = "ASSISTANT:\n" + assistant_text.strip() + "\n\n"
            safe_write_file(current_path, to_write, mode="a")

            # Keep session state pointing to the file we wrote to
            st.session_state.current_chat_file = current_path

            return current_path

        except Exception as e:
            try:
                st.sidebar.error(f"Failed to write assistant message to history: {e}")
            except Exception:
                pass
            return path

    # ---------- NORMAL USER MESSAGE ----------
    if prompt and not st.session_state.regen:

        st.session_state.last_prompt = prompt

        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # FIX: Create chat file only now (append_user_to_file will create it if needed),
        # rename it based on first prompt, and update session_state.current_chat_file.
        append_user_to_file(st.session_state.get("current_chat_file"), prompt)

    if st.session_state.voice:
        prompt = st.session_state.voice_prompt
        st.session_state.last_prompt = prompt
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # FIX: Create chat file only now for voice prompts as well
        append_user_to_file(st.session_state.get("current_chat_file"), prompt)

        st.session_state.voice = False
        st.session_state.voice_prompt = None

    # ---------- REGENERATE ----------
    if st.session_state.regen:

        prompt = st.session_state.last_prompt

        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages.pop()

        st.session_state.regen = False

    # ---------- GENERATE ----------
    if prompt:

        CONTEXT_LIMIT = 10

        context_messages = [
            {"role": "system", "content": config["system_prompt"]}
        ] + st.session_state.messages[-CONTEXT_LIMIT:]

        # -------- FILE CONTEXT --------
        if file_text:
            context_messages[0]["content"] += (
                "\n\nUse the following file content to answer the user question.\n\n"
                + file_text[:12000]
            )

        # -------- WEB SEARCH --------
        if web_mode:
            with st.spinner("🌐 Searching internet..."):
                search_results = search_web(prompt)
            context_messages[0]["content"] += (
                "\n\nUse the following web search results if helpful.\n\n"
                + search_results
            )

        # -------- RANDOMNESS BOOST --------
        temp = temperature

        if prompt == st.session_state.last_prompt:
            temp = min(temperature + random.uniform(0.2, 0.5), 1.5)

        # ---------- GENERATE ASSISTANT RESPONSE ----------
        if client:
            with st.chat_message("assistant"):

                placeholder = st.empty()
                full_response = ""

                stream = client.chat.completions.create(
                    model=model,
                    messages=context_messages,
                    temperature=temp,
                    max_tokens=max_tokens,
                    stream=True
                )

                finish_reason = None

                for chunk in stream:
                    content = chunk.choices[0].delta.content or ""
                    full_response += content
                    finish_reason = chunk.choices[0].finish_reason
                    placeholder.markdown(full_response + "▌")

                continue_count = 0
                MAX_CONTINUE = 3

                while finish_reason == "length" and continue_count < MAX_CONTINUE:
                    continue_count += 1
                    continuation_messages = context_messages + [{
                        "role": "assistant",
                        "content": full_response[-2000:]
                    }]

                    stream = client.chat.completions.create(
                        model=model,
                        messages=continuation_messages,
                        temperature=temp,
                        max_tokens=max_tokens,
                        stream=True
                    )

                    for chunk in stream:
                        content = chunk.choices[0].delta.content or ""
                        full_response += content
                        finish_reason = chunk.choices[0].finish_reason
                        placeholder.markdown(full_response + "▌")

                placeholder.markdown(full_response)
                st.session_state.last_response = full_response
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })

            # Append assistant response to current chat file (uses updated session_state path)
            append_assistant_to_file(st.session_state.get("current_chat_file"), full_response)

    # ---------------- BUTTONS SIDE BY SIDE ----------------
    if st.session_state.last_prompt and st.session_state.last_response:

        c1, c2, c3, c4, c5 = st.columns([4, 4, 1.3, 1.3, 1.5])

        # -------- Speak Button --------
        with c3:
            if st.button("🔊 Speak"):

                voice_map = {
                    "Default": "en-US-AriaNeural",
                    "English Male": "en-US-GuyNeural",
                    "English Female": "en-US-AriaNeural",
                    "Hindi Female": "hi-IN-SwaraNeural"
                }
                selected_voice = voice_map.get(st.session_state.voice_settings["voice"], "en-US-AriaNeural")

                rate_map = {
                    "High": "+90%",
                    "Normal": "+1%",
                    "Slow": "-30%"
                }
                selected_rate_percent = rate_map.get(st.session_state.voice_settings["rate"], "1%")

                tts_file = "temp_response.mp3"

                async def generate_tts(text, filename, voice, rate):
                    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
                    await communicate.save(filename)

                asyncio.run(generate_tts(
                    st.session_state.last_response,
                    tts_file,
                    selected_voice,
                    selected_rate_percent
                ))

                try:
                    with open(tts_file, "rb") as f:
                        audio_bytes = f.read()

                    b64 = base64.b64encode(audio_bytes).decode()

                    st.markdown(
                        f"""
                        <audio autoplay controls>
                            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                        </audio>
                        """,
                        unsafe_allow_html=True
                    )
                except Exception:
                    st.error("Failed to play TTS audio.")

        # -------- Regenerate Button --------
        with c4:
            if st.button("🔄Regrte", key="regen_btn"):
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
                    st.session_state.messages.pop()

                st.session_state.regen = True
                st.rerun()

def show_without_login():
    import os
    import random
    import streamlit as st
    from groq import Groq
    from ddgs import DDGS
    import pandas as pd
    import speech_recognition as sr
    from deep_translator import GoogleTranslator
    import edge_tts
    import asyncio
    import base64        
    from streamlit_mic_recorder import mic_recorder
    import tempfile

    # ---------------- PAGE CONFIG ----------------
    st.set_page_config(
        page_title="AI Chat Assistant",
        page_icon="🤖",
        layout="wide"
    )

    #==================== FUNCTION ==========================
    # ------------------- VOICE INPUT FUNCTION -------------------
    def voice_input_to_prompt(audio):

        temp_path = None

        try:
            raw = audio.get("bytes")

            # agar bytes base64 me aaye
            if isinstance(raw, str):
                raw = base64.b64decode(raw)

            # temp file create
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
            temp_path = tf.name
            tf.write(raw)
            tf.close()

            # Groq Whisper STT
            transcription = client.audio.transcriptions.create(
                file=(temp_path, open(temp_path, "rb").read()),
                model="whisper-large-v3",
                response_format="json",
                language="hi"
            )

            text = transcription.text

            translated = GoogleTranslator(
                source="auto",
                target="en"
            ).translate(text)

            st.success(f"🗣 You said: {text}")
            st.info(f"🌍 English: {translated}")

            st.session_state.voice_prompt = translated
            return translated

        except Exception as e:
            st.error(f"⚠️ Error: {e}")
            return None

    # -------- WEB SEARCH --------
    def search_web(query, results=5):

        output = []

        try:
            with DDGS() as ddgs:

                for r in ddgs.text(query, max_results=results):

                    title = r["title"]
                    body = r["body"]
                    link = r["href"]

                    output.append(f"{title}\n{body}\n{link}")

        except:
            return "Web search failed."

        return "\n\n".join(output)



    # ---------------- SESSION STATE ----------------
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_prompt" not in st.session_state:
        st.session_state.last_prompt = None
        

    if "regen" not in st.session_state:
        st.session_state.regen = False

    if "voice_prompt" not in st.session_state:
        st.session_state.voice_prompt = None
        st.session_state.last_response=None

    if "voice" not in st.session_state:
        st.session_state.voice = False

    # ---------------- CUSTOM CSS (UI / COLORS ONLY) ----------------
    st.markdown(
        """
        <style>
        /* Overall app background: very light, warm gradient */
        .stApp {
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
            color-scheme: light;
        }

        /* Main container: centered, comfortable width */
        .main .block-container {
            max-width: 1100px;
            padding-top: 18px;
            padding-left: 28px;
            padding-right: 28px;
            padding-bottom: 28px;
            margin: 0 auto;
        }

        /* Sidebar: soft, friendly blue with subtle shadow */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f6f9ff 0%, #eef6ff 100%);
            border-right: 1px solid rgba(18,58,107,0.06);
            padding: 18px 16px 24px 16px;
            box-shadow: 0 2px 8px rgba(15, 30, 60, 0.03);
        }

        /* Sidebar title and labels color */
        [data-testid="stSidebar"] .css-1d391kg h1,
        [data-testid="stSidebar"] .css-1d391kg h2,
        [data-testid="stSidebar"] .css-1d391kg h3,
        [data-testid="stSidebar"] .css-1d391kg label {
            color: #0f3a66;
        }

        /* Tidy the sidebar widgets spacing */
        [data-testid="stSidebar"] .stButton, 
        [data-testid="stSidebar"] .stRadio, 
        [data-testid="stSidebar"] .stSelectbox {
            margin-top: 8px;
            margin-bottom: 8px;
        }

        /* App title: centered and prominent */
        .css-18e3th9 h1, .css-1v3fvcr h1 {
            text-align: center;
            color: #0f3a66;
            font-weight: 700;
            margin-bottom: 6px;
        }

        /* Subtitle / small text color */
        .css-1v0mbdj, .css-1v0mbdj p {
            color: #2b4a6f;
        }

        /* Chat message container: rounded, airy */
        .stChatMessage {
            border-radius: 14px;
            padding: 12px 16px;
            margin-bottom: 12px;
            box-shadow: 0 1px 0 rgba(16,24,40,0.03);
            font-size: 15px;
            line-height: 1.5;
            max-width: 88%;
            word-wrap: break-word;
        }

        /* User messages: soft cyan bubble aligned right */
        .stChatMessage[data-testid="stChatMessage-user"] {
            background: linear-gradient(180deg, #e9fbff 0%, #e6f7ff 100%);
            border: 1px solid #bfeeff;
            color: #08324a;
            margin-left: auto;
            margin-right: 6px;
        }

        /* Assistant messages: warm cream bubble aligned left */
        .stChatMessage[data-testid="stChatMessage-assistant"] {
            background: linear-gradient(180deg, #fffdf6 0%, #fff9e6 100%);
            border: 1px solid #ffe9a8;
            color: #3b2f00;
            margin-right: auto;
            margin-left: 6px;
        }

        /* System / other messages: subtle gray */
        .stChatMessage[data-testid="stChatMessage-system"] {
            background: #f6f7fb;
            border: 1px solid #e6e9f2;
            color: #2b3a55;
            margin-left: 6px;
            margin-right: 6px;
        }

        /* Chat input styling: rounded, clear */
        .stChatInput textarea, .stChatInput input {
            border-radius: 10px;
            border: 1px solid #d6e6ff;
            padding: 10px 12px;
            background: #ffffff;
            color: #0b2b45;
            box-shadow: none;
        }

        /* Placeholder caret color for input */
        .stChatInput textarea::placeholder, .stChatInput input::placeholder {
            color: #7a9bb8;
        }

        /* Primary buttons: friendly blue */
        .stButton>button {
            background-color: #0b79d0;
            color: #ffffff;
            border-radius: 8px;
            padding: 8px 14px;
            border: none;
            font-weight: 600;
            box-shadow: 0 2px 6px rgba(11,121,208,0.12);
        }
        .stButton>button:hover {
            background-color: #0961a8;
            color: #ffffff;
        }

        /* Danger / clear button: subtle red outline */
        [data-testid="stSidebar"] .stButton>button:has(svg[aria-hidden="true"]) {
            background-color: #fff6f6;
            color: #a12b2b;
            border: 1px solid rgba(161,43,43,0.08);
            box-shadow: none;
        }

        /* Regenerate button: slightly different accent */
        button[kind="primary"][title="regen_btn"], .stButton>button[aria-label="🔄 Regenerate"] {
            background-color: #16a34a;
        }

        /* Fix file uploader text display */
    .stFileUploader [data-testid="stFileUploadLabel"] {
        position: relative;   /* remove overlay issues */
        z-index: 2;
        color: #0b2b45;      /* visible text color */
        font-weight: 500;
    }

    /* Optional: make container slightly taller so name fits */
    .stFileUploader > div {
        min-height: 50px;    /* ensure text fits */
    }

        /* Sidebar separators */
        [data-testid="stSidebar"] hr {
            border: none;
            height: 1px;
            background: linear-gradient(90deg, rgba(18,58,107,0.06), rgba(18,58,107,0.02));
            margin: 12px 0;
        }

        /* Links color */
        a {
            color: #0b79d0;
        }

        /* Hide default Streamlit header for a cleaner look */
        header[data-testid="stHeader"] {
            display: none;
        }

        /* Slight spacing improvement for chat area */
        .css-1lcbmhc.e1fqkh3o3 {
            gap: 14px;
        }

        /* Responsive tweaks */
        @media (max-width: 900px) {
            .main .block-container {
                padding-left: 12px;
                padding-right: 12px;
            }
            .stChatMessage {
                font-size: 14px;
                max-width: 96%;
            }
            [data-testid="stSidebar"] {
                padding-left: 12px;
                padding-right: 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    # ---------------- API KEY ----------------
    api_key = st.secrets["GROQ_API_KEY"]

    client = None
    if api_key:
        client = Groq(api_key=api_key)

    # ---------------- SIDEBAR ----------------
    st.sidebar.title("⚙️ AI Settings")

    mode = st.sidebar.radio(
        "Select AI Mode",
        ["FAST", "THINK HARD","CODER"]
    )

    # ---------------- AI SETTINGS ----------------
    with st.sidebar.expander("⚙️ Model Settings", expanded=True):
        
        # -------- MODE CONFIG --------
        mode_configs = {
            "FAST": {
                "model": "llama-3.1-8b-instant",
                "temperature": 0.3,
                "max_tokens": 300,
                "system_prompt": "Give short and direct answers."
            },
            
            "THINK HARD": {
                "model": "qwen/qwen3-32b",
                "temperature": 0.2,
                "max_tokens": 1500,
                "system_prompt": "Think step by step and solve complex problems."
            },
            "CODER": {
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.2,
                "max_tokens": 1200,
                "system_prompt": "You are an expert programmer. Write clean, correct and optimized code."
            }
        }

        config = mode_configs[mode]
        
        # -------- MODEL SELECT --------
        model = st.selectbox(
            "Model",
            [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "qwen/qwen3-32b"
            ],
            index=0 if config["model"] == "llama-3.1-8b-instant"
            else 1 if config["model"] == "llama-3.3-70b-versatile"
            else 2 if config["model"] == "qwen/qwen3-32b"
            else 3
        )

        # -------- MAX TOKENS SLIDER --------
        max_tokens = st.slider(
            "Max Tokens",
            100,
            4096,
            config["max_tokens"]
        )

    temperature = config["temperature"]
    web_mode = st.sidebar.toggle("🌐 Internet Access")

    # -------- FILE UPLOAD --------
    uploaded_file = st.sidebar.file_uploader(
        "📂 Upload file (CSV / TXT)",
        type=["csv","txt"]
    )

    file_text = ""

    if uploaded_file:

        try:

            if uploaded_file.type == "text/csv":

                df = pd.read_csv(uploaded_file)
                file_text = df.to_string()

            elif uploaded_file.type == "text/plain":

                file_text = uploaded_file.read().decode("utf-8")

        except:
            file_text = "Failed to read file."


    # ---------------- VOICE SETTINGS ----------------
    if "voice_settings" not in st.session_state:
        st.session_state.voice_settings = {
            "rate": "Normal",      # default
            "volume": 1.0,
            "voice": None
        }
        st.session_state.last_response = None

    with st.sidebar.expander("🔊 Voice Settings"):
    # Fixed rate options instead of slider
        rate_choice = st.selectbox(
            "Speech Rate",
            [ "Normal","High", "Slow"]
        )
        st.session_state.voice_settings["rate"] = rate_choice
        voice_choice = st.selectbox(
            "Voice",
            [
                "Default",
                "English Male",
                "English Female",
                
                "Hindi Female"
            ]
        )
        st.session_state.voice_settings["voice"] = voice_choice

    st.sidebar.markdown("---")

    # ------------------- SIDEBAR BUTTONS SIDE BY SIDE -------------------
    col1, col2 = st.sidebar.columns([1, 1])  # two equal-width columns

    # -------- Clear Chat Button --------
    with col1:
        if st.button("🗑 Clear Chat"):
            st.session_state.messages = []
            st.session_state.last_prompt = None
            st.session_state.voice_prompt = None
            st.rerun()

    with col2:

        audio = mic_recorder(
            start_prompt="🎤 Start recording",
            stop_prompt="⏹ Stop recording",
            just_once=True
        )

        if audio:
            
            result = voice_input_to_prompt(audio)
            if result:
                st.session_state.voice = True
                st.rerun()

    # ---------------- TITLE ----------------
    st.title("🤖 AI Chat Assistant")


    # ---------------- DISPLAY HISTORY ----------------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ---------------- USER INPUT ----------------
    prompt = st.chat_input("Ask anything...")


    # ---------- NORMAL USER MESSAGE ----------
    if prompt and not st.session_state.regen:

        st.session_state.last_prompt = prompt

        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

    if st.session_state.voice:
        prompt = st.session_state.voice_prompt
        st.session_state.last_prompt = prompt
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        st.session_state.voice=False
        st.session_state.voice_prompt=None

    # ---------- REGENERATE ----------
    if st.session_state.regen:

        prompt = st.session_state.last_prompt

        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages.pop()

        st.session_state.regen = False

    # ---------- GENERATE ----------
    if prompt:

        CONTEXT_LIMIT = 10

        context_messages = [
            {"role": "system", "content": config["system_prompt"]}
        ] + st.session_state.messages[-CONTEXT_LIMIT:]

        # -------- FILE CONTEXT --------
        if file_text:

            context_messages[0]["content"] += (
                "\n\nUse the following file content to answer the user question.\n\n"
                + file_text[:12000]
            )

        # -------- WEB SEARCH --------
        if web_mode: 

            with st.spinner("🌐 Searching internet..."):
                search_results = search_web(prompt)

            context_messages[0]["content"] += (
                "\n\nUse the following web search results if helpful.\n\n"
                + search_results
            )
        
        # -------- RANDOMNESS BOOST --------
        temp = temperature

        if prompt == st.session_state.last_prompt:
            temp = min(temperature + random.uniform(0.2, 0.5), 1.5)

        # ---------- GENERATE ASSISTANT RESPONSE ----------
        if client:
            with st.chat_message("assistant"):

                placeholder = st.empty()
                full_response = ""

                stream = client.chat.completions.create(
                    model=model,
                    messages=context_messages,
                    temperature=temp,
                    max_tokens=max_tokens,
                    stream=True
                )

                finish_reason = None

                for chunk in stream:
                    content = chunk.choices[0].delta.content or ""
                    full_response += content
                    finish_reason = chunk.choices[0].finish_reason
                    placeholder.markdown(full_response + "▌")

                continue_count = 0
                MAX_CONTINUE = 3

                while finish_reason == "length" and continue_count < MAX_CONTINUE:
                    continue_count += 1
                    continuation_messages = context_messages + [{
                        "role": "assistant",
                        "content": full_response[-2000:]
                    }]

                    stream = client.chat.completions.create(
                        model=model,
                        messages=continuation_messages,
                        temperature=temp,
                        max_tokens=max_tokens,
                        stream=True
                    )

                    for chunk in stream:
                        content = chunk.choices[0].delta.content or ""
                        full_response += content
                        finish_reason = chunk.choices[0].finish_reason
                        placeholder.markdown(full_response + "▌")

                placeholder.markdown(full_response)
                st.session_state.last_response=full_response
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })

    # ---------------- BUTTONS SIDE BY SIDE ----------------
    if st.session_state.last_prompt and st.session_state.last_response:

        c1, c2, c3, c4, c5 = st.columns([4, 4, 1.3, 1.3, 1.5])

        # -------- Speak Button --------
        with c3:
            if st.button("🔊 Speak"):
                
                # Voice mapping
                voice_map = {
                    "Default": "en-US-AriaNeural",
                    "English Male": "en-US-GuyNeural",
                    "English Female": "en-US-AriaNeural",
                    
                    "Hindi Female": "hi-IN-SwaraNeural"
                }
                selected_voice = voice_map.get(st.session_state.voice_settings["voice"], "en-US-AriaNeural")

                # Rate conversion: edge-tts uses percentage (default 0%)
                # Slider 80–300 -> rate -50% to +50% roughly
                # Rate mapping to edge-tts percentage
                rate_map = {
                                "High": "+90%",    # fast speech
                                "Normal": "+1%",   # normal speed (0% kabhi invalid hota hai)
                                "Slow": "-30%"   # slower speech
                            }
                selected_rate_percent = rate_map.get(st.session_state.voice_settings["rate"], "1%")

                tts_file = "temp_response.mp3"

                async def generate_tts(text, filename, voice, rate):
                    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
                    await communicate.save(filename)

                asyncio.run(generate_tts(
                    st.session_state.last_response,
                    tts_file,
                    selected_voice,
                    selected_rate_percent
                ))

                with open(tts_file, "rb") as f:
                    audio_bytes = f.read()

                b64 = base64.b64encode(audio_bytes).decode()

                st.markdown(
                    f"""
                    <audio autoplay controls>
                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    """,
                    unsafe_allow_html=True
                )

        # -------- Regenerate Button --------
        with c4:
            if st.button("🔄Regrte", key="regen_btn"):
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
                    st.session_state.messages.pop()

                st.session_state.regen = True
                st.rerun()


def check_login_and_run(session_state):
    if not session_state.get("logged_in", False):
        show_without_login()
    else:
        name=session_state.current_user
        show_with_login(session_state)