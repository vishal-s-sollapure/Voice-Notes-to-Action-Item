import os
import json
import tempfile
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

# --- Page Configuration ---
st.set_page_config(
    page_title="Voice Notes to Action Items | GenAI Task Extractor",
    page_icon="🎙️",
    layout="wide"
)

# --- Custom Styling (Earthy Organic Palette) ---
st.markdown("""
<style>
    .stApp {
        background-color: #121110;
        color: #E6E1DA;
    }
    .metric-card {
        background-color: #1C1A17;
        border: 1px solid #38332C;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .high-priority { border-left: 5px solid #E56B6F; }
    .medium-priority { border-left: 5px solid #E0A96D; }
    .low-priority { border-left: 5px solid #84A59D; }
    .badge {
        background-color: #2A2621;
        color: #D4A373;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- Structured Output Schema ---
class TaskItem(BaseModel):
    task: str = Field(description="Actionable summary of the task.")
    owner: Optional[str] = Field(description="Assigned person or 'Unassigned'.")
    due_date: Optional[str] = Field(description="Specific date/timeframe mentioned, or 'Not specified'.")
    priority: str = Field(description="Priority classification: High, Medium, or Low.")

class AudioAnalysisResult(BaseModel):
    transcript: str = Field(description="Full verbatim speech-to-text transcript.")
    summary: str = Field(description="Brief 2-sentence executive summary of the audio note.")
    action_items: List[TaskItem]

# --- Sidebar Controls ---
with st.sidebar:
    st.title("⚙️ Engine Settings")
    api_key = st.text_input("Gemini API Key", type="password", help="Enter your Gemini API key from Google AI Studio.")
    selected_model = st.selectbox("Gemini Model", ["gemini-2.5-flash", "gemini-2.5-pro"])
    st.markdown("---")
    st.markdown("💡 **Need an API Key?**\nGet a free key from [Google AI Studio](https://aistudio.google.com).")

st.title("🎙️ Voice Notes → Action Items")
st.caption("AI-powered voice intelligence tool that converts raw audio notes into structured, trackable team tasks.")

if not api_key:
    st.warning("⚠️ Please enter your Google Gemini API Key in the sidebar to proceed.")
    st.stop()

# --- Main Audio Input Controls ---
st.subheader("1. Record or Upload Audio Note")
col1, col2 = st.columns([1, 1])

audio_source = None
with col1:
    uploaded_file = st.file_uploader("Upload Audio File", type=["mp3", "wav", "m4a", "ogg", "flac"])
    if uploaded_file:
        audio_source = uploaded_file

with col2:
    recorded_audio = st.audio_input("Record Live Audio")
    if recorded_audio:
        audio_source = recorded_audio

if audio_source:
    st.audio(audio_source)
    
    if st.button("🚀 Process Voice Note", type="primary", use_container_width=True):
        client = genai.Client(api_key=api_key)
        
        with st.status("⚡ Analyzing audio with Gemini...", expanded=True) as status:
            try:
                # Save buffer to temporary file for upload
                suffix = f".{audio_source.name.split('.')[-1]}" if hasattr(audio_source, 'name') else ".wav"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(audio_source.getbuffer())
                    tmp_path = tmp.name

                status.write("📤 Uploading media file...")
                media_file = client.files.upload(file=tmp_path)

                status.write("🧠 Extracting transcript & structured action items...")
                prompt = """
                Extract a complete verbatim transcript, a short executive summary, and all structured action items from this audio.
                Ensure priority classifications (High, Medium, Low) are accurately deduced from urgency context.
                """

                response = client.models.generate_content(
                    model=selected_model,
                    contents=[media_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AudioAnalysisResult,
                    ),
                )

                # Parse JSON output safely
                data = json.loads(response.text)
                
                # Cleanup temp file
                os.remove(tmp_path)
                status.update(label="✅ Processing Complete!", state="complete", expanded=False)

                # --- Results UI Display ---
                st.markdown("---")
                st.subheader("📌 Executive Summary")
                st.info(data.get("summary", "No summary provided."))

                st.subheader("🎙️ Verbatim Transcript")
                with st.expander("Click to view full transcript text"):
                    st.write(data.get("transcript", ""))

                st.subheader("📋 Action Items & Task Cards")
                action_items = data.get("action_items", [])
                
                if not action_items:
                    st.warning("No clear action items detected in this voice note.")
                else:
                    card_cols = st.columns(2)
                    for idx, item in enumerate(action_items):
                        prio = item.get("priority", "Low").capitalize()
                        prio_class = f"{prio.lower()}-priority"
                        
                        with card_cols[idx % 2]:
                            st.markdown(f"""
                            <div class="metric-card {prio_class}">
                                <h3>{item.get('task')}</h3>
                                <p><strong>👤 Assigned To:</strong> <span class="badge">{item.get('owner') or 'Unassigned'}</span></p>
                                <p><strong>📅 Due Date:</strong> {item.get('due_date') or 'Not specified'}</p>
                                <p><strong>⚡ Priority:</strong> {prio}</p>
                            </div>
                            """, unsafe_allow_html=True)

                # Export Option
                st.markdown("---")
                st.download_button(
                    label="📥 Download Structured JSON Output",
                    data=json.dumps(data, indent=2),
                    file_name="voice_action_items.json",
                    mime="application/json"
                )

            except Exception as e:
                status.update(label="❌ Processing Error", state="error", expanded=True)
                st.error(f"Failed to process audio: {str(e)}")