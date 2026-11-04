import os
import json
import streamlit as st
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Voice Notes → Action Items | GenAI Portfolio",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Recruiter-Ready Earthy Dark Theme CSS
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* Global Background and Typography */
    .stApp {
        background-color: #121110;
        color: #FAEDCD;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #191816;
        border-right: 1px solid #2B2927;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #FAEDCD !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(120deg, #FAEDCD, #D4A373);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }

    .sub-caption {
        color: #A8A29E;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    /* Executive Summary Callout */
    .summary-card {
        background: #1C1A18;
        border-left: 4px solid #D4A373;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        margin: 1.25rem 0 1.75rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    .summary-title {
        color: #D4A373;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }

    .summary-text {
        color: #FAEDCD;
        font-size: 1.05rem;
        line-height: 1.6;
        margin: 0;
    }

    /* Dynamic Priority Task Cards */
    .task-card {
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        background-color: #1A1816;
    }
    
    .task-card:hover {
        transform: translateY(-2px);
    }

    .task-card-high {
        border: 1.5px solid #E63946;
        box-shadow: 0 4px 18px rgba(230, 57, 70, 0.12);
    }

    .task-card-medium {
        border: 1.5px solid #F4A261;
        box-shadow: 0 4px 18px rgba(244, 162, 97, 0.12);
    }

    .task-card-low {
        border: 1.5px solid #2A9D8F;
        box-shadow: 0 4px 18px rgba(42, 157, 143, 0.12);
    }

    .task-title {
        font-size: 1.12rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .badge {
        font-size: 0.72rem;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .badge-high {
        background-color: rgba(230, 57, 70, 0.18);
        color: #FF6B6B;
        border: 1px solid rgba(230, 57, 70, 0.4);
    }

    .badge-medium {
        background-color: rgba(244, 162, 97, 0.18);
        color: #F4A261;
        border: 1px solid rgba(244, 162, 97, 0.4);
    }

    .badge-low {
        background-color: rgba(42, 157, 143, 0.18);
        color: #2A9D8F;
        border: 1px solid rgba(42, 157, 143, 0.4);
    }

    .meta-row {
        display: flex;
        justify-content: space-between;
        margin-top: 0.6rem;
        font-size: 0.9rem;
        color: #A8A29E;
        border-top: 1px solid #292624;
        padding-top: 0.6rem;
    }

    .meta-value {
        color: #FAEDCD;
        font-weight: 600;
    }

    /* Primary Buttons with Accent Color */
    button[kind="primary"] {
        background-color: #D4A373 !important;
        color: #121110 !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.4rem !important;
        transition: all 0.2s ease-in-out !important;
    }

    button[kind="primary"]:hover {
        background-color: #E2B78D !important;
        box-shadow: 0 4px 14px rgba(212, 163, 115, 0.3) !important;
    }

    /* Tab and Expander Accents */
    div[data-testid="stExpander"] {
        background-color: #181715;
        border: 1px solid #2B2927;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Pydantic Structured Output Schema
# ---------------------------------------------------------
class PriorityLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class ActionItem(BaseModel):
    task: str = Field(description="The concise action item or task to be completed.")
    priority: PriorityLevel = Field(description="Priority categorization: High, Medium, or Low.")
    owner: Optional[str] = Field(default="Unassigned", description="Name or role of the person responsible, or 'Unassigned' if not mentioned.")
    due_date: Optional[str] = Field(default="Not specified", description="Deadline or timeframe mentioned, or 'Not specified' if absent.")

class ExtractionResult(BaseModel):
    transcript: str = Field(description="Full word-for-word transcript of the spoken recording.")
    executive_summary: str = Field(description="Strictly a 2-sentence executive summary capturing the core topics and decisions.")
    action_items: List[ActionItem] = Field(description="Array of structured action items extracted from the audio.")

# ---------------------------------------------------------
# Sidebar: Settings & Dual-Engine Selection
# ---------------------------------------------------------
default_api_key = os.environ.get("GEMINI_API_KEY", "")
if not default_api_key:
    try:
        default_api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        default_api_key = ""

with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    
    api_key = st.text_input(
        "Google Gemini API Key",
        value=default_api_key,
        type="password",
        help="Get your free API key at https://aistudio.google.com/",
        placeholder="AIzaSy...",
    )

    st.markdown("---")
    st.markdown("### 🧠 Model Selection")
    model_choice = st.selectbox(
        "Gemini Engine",
        options=["gemini-3.8-flash", "gemini-3.8-pro", "gemini-2.5-flash"],
        index=0,
        format_func=lambda x: "⚡ Gemini 3.8 Flash (Latest & Recommended)" if x == "gemini-3.8-flash" else ("🔬 Gemini 3.8 Pro (Deep Reasoning)" if x == "gemini-3.8-pro" else "⚡ Gemini 2.5 Flash (Legacy)"),
        help="Select between Gemini 3.8 Flash for ultra-fast multimodal processing or 3.8 Pro for deep reasoning.",
    )

    st.markdown("---")
    st.markdown("### 📋 Portfolio Architecture")
    st.caption(
        """
        - **Audio Ingestion**: Native PCM/WAV/MP3 Stream
        - **Multimodal LLM**: Native Gemini 3.8 Engine
        - **Schema Validation**: Pydantic v2 Type Contract
        - **Frontend**: Streamlit + Custom Dark Theme
        """
    )
    st.markdown("[Get Free API Key](https://aistudio.google.com/) ↗")

# Guard: Require API key
if not api_key:
    st.info("👈 Please enter your **Google Gemini API Key** in the sidebar to begin.")
    st.stop()

# Initialize Google GenAI Client
client = genai.Client(api_key=api_key) if api_key else None

# ---------------------------------------------------------
# Header Section
# ---------------------------------------------------------
st.markdown('<div class="main-title">🎙️ Voice Notes → Action Items</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-caption">Enterprise-grade multimodal audio transcription and structured action-item extraction powered by <b>Google Gemini</b> and <b>Pydantic</b>.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 1. Multi-Modal Audio Input
# ---------------------------------------------------------
st.markdown("### 1. Ingest Voice Recording")

tab_upload, tab_record = st.tabs(["📁 Upload Audio File", "🎤 Record Live Audio"])
audio_file = None

with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload audio recording",
        type=["mp3", "wav", "m4a", "ogg"],
        help="Supported formats: MP3, WAV, M4A, OGG up to 200MB.",
    )
    if uploaded_file:
        audio_file = uploaded_file

with tab_record:
    st.caption("Allow microphone access in your browser when prompted to record directly.")
    recorded_file = st.audio_input(
        "Record directly in browser",
        help="Microphone permission required.",
    )
    if recorded_file:
        audio_file = recorded_file

# ---------------------------------------------------------
# 2. Audio Processing Logic
# ---------------------------------------------------------
if audio_file:
    st.audio(audio_file)

    process_btn = st.button("🚀 Process Recording with Gemini", type="primary", use_container_width=True)

    if process_btn:
        with st.status("Analyzing audio stream with Gemini...", expanded=True) as status:
            try:
                status.write(f"Feeding raw audio directly to `{model_choice}`...")
                
                # Prepare Multimodal Part
                mime_type = audio_file.type or "audio/wav"
                audio_part = types.Part.from_bytes(
                    data=audio_file.getvalue(),
                    mime_type=mime_type,
                )

                prompt = """
                You are an elite executive assistant and project manager listening to this voice note.
                1. Provide an accurate word-for-word transcript.
                2. Formulate a concise, exact 2-sentence executive summary summarizing the key conversation points and decisions.
                3. Extract all explicit and implied action items, tasks, deadlines, and assigned persons.
                4. Categorize priority strictly as 'High', 'Medium', or 'Low'.
                5. If an assignee or due date is not mentioned or ambiguous, set them to 'Unassigned' or 'Not specified'.
                """

                status.write("Enforcing strict Pydantic JSON schema...")
                try:
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=[audio_part, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ExtractionResult,
                            temperature=0.2,
                        ),
                    )
                except Exception as call_err:
                    err_msg = str(call_err)
                    if model_choice != "gemini-3.8-flash" and ("no longer available" in err_msg or "404" in err_msg or "NOT_FOUND" in err_msg):
                        status.write("Selected model deprecated. Auto-switching to `gemini-3.8-flash`...")
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=[audio_part, prompt],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=ExtractionResult,
                                temperature=0.2,
                            ),
                        )
                    else:
                        raise call_err

                status.update(label="Audio Successfully Processed!", state="complete", expanded=False)

                # Validate Structured Output against Pydantic
                result = ExtractionResult.model_validate_json(response.text)

            except Exception as exc:
                status.update(label="Processing Failed", state="error", expanded=True)
                st.error(f"❌ Gemini Processing Error: {str(exc)}")
                st.stop()

        # ---------------------------------------------------------
        # 3. Output Presentation
        # ---------------------------------------------------------

        # Executive Summary
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-title">📌 Executive Summary</div>
                <div class="summary-text">{result.executive_summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Interactive Expandable Transcript
        with st.expander("📝 Full Word-for-Word Transcript", expanded=False):
            st.markdown(f"> *\"{result.transcript}\"*")

        # Action Items Header + Download Button Row
        col_header, col_dl = st.columns([3, 1])
        with col_header:
            st.markdown(f"### ✅ Action Items ({len(result.action_items)})")
        with col_dl:
            json_export = result.model_dump_json(indent=2)
            st.download_button(
                label="📥 Export JSON",
                data=json_export,
                file_name="action_items.json",
                mime="application/json",
                use_container_width=True,
            )

        # Action Items Grid
        if not result.action_items:
            st.warning("No actionable tasks identified in this recording.")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(result.action_items):
                col = cols[idx % 2]
                priority_val = item.priority.value if hasattr(item.priority, "value") else str(item.priority)
                priority_lower = priority_val.lower()

                # Dynamic style classes based on priority
                if priority_lower == "high":
                    card_class = "task-card-high"
                    badge_class = "badge-high"
                    icon = "🔴"
                elif priority_lower == "medium":
                    card_class = "task-card-medium"
                    badge_class = "badge-medium"
                    icon = "🟠"
                else:
                    card_class = "task-card-low"
                    badge_class = "badge-low"
                    icon = "🟢"

                with col:
                    st.markdown(
                        f"""
                        <div class="task-card {card_class}">
                            <div class="task-title">
                                <span>{icon} {item.task}</span>
                                <span class="badge {badge_class}">{priority_val}</span>
                            </div>
                            <div class="meta-row">
                                <span>👤 Owner</span>
                                <span class="meta-value">{item.owner or 'Unassigned'}</span>
                            </div>
                            <div class="meta-row">
                                <span>📅 Due Date</span>
                                <span class="meta-value">{item.due_date or 'Not specified'}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
