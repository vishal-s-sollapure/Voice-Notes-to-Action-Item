import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

# Page configuration
st.set_page_config(page_title="Voice Notes to Action Items", page_icon="🎙️", layout="wide")
st.title("🎙️ Voice Notes → Action Items")
st.caption("Transcribe voice notes and extract tasks, priorities, and owners using Gemini.")

# Sidebar API Key
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    st.info("Get your key from Google AI Studio")

if not api_key:
    st.warning("Please enter your Google Gemini API Key in the sidebar to proceed.")
    st.stop()

# Initialize Client
client = genai.Client(api_key=api_key)

# Structured Output Schema
class ActionItem(BaseModel):
    task: str = Field(description="The action item or task to be completed.")
    priority: str = Field(description="Priority level: High, Medium, or Low.")
    owner: Optional[str] = Field(description="Person responsible, or 'Unassigned'.")
    due_date: Optional[str] = Field(description="Deadline mentioned, or 'Not specified'.")

class ExtractionResult(BaseModel):
    transcript: str = Field(description="Full word-for-word transcript of the audio.")
    action_items: List[ActionItem] = Field(description="List of extracted tasks.")

# 1. Screen & Audio Input
st.subheader("1. Provide Audio Input")
tab1, tab2 = st.tabs(["Upload Audio File", "Record Audio"])
audio_file = None

with tab1:
    uploaded = st.file_uploader("Upload an audio file", type=["mp3", "wav", "m4a", "ogg"])
    if uploaded:
        audio_file = uploaded

with tab2:
    st.info("Allow microphone access when your browser asks. If recording fails, use the Upload Audio File tab instead.")
    recorded = st.audio_input(
        "Record a short voice note",
        help="Microphone access must be allowed for this site. Check your browser's site permissions if recording does not start.",
    )
    if recorded:
        audio_file = recorded

# Processing Logic
if audio_file:
    st.audio(audio_file)
    
    if st.button("Process Voice Note", type="primary"):
        with st.status("Processing Audio with Gemini...", expanded=True) as status:
            try:
                status.write("Transcribing audio and extracting action items...")
                prompt = """
                Listen carefully to this audio file.
                1. Provide an accurate word-for-word transcript.
                2. Extract all action items, assignees, dates, and priorities.
                If information like owner or due date is missing or ambiguous, mark it as 'Unassigned' or 'Not specified'.
                """
                audio_part = types.Part.from_bytes(
                    data=audio_file.getvalue(),
                    mime_type=audio_file.type or "audio/wav",
                )

                # Gemini Flash call
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[audio_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ExtractionResult,
                    ),
                )
                
                status.update(label="Processing Complete!", state="complete", expanded=False)
                
                # Parse JSON output
                result = ExtractionResult.model_validate_json(response.text)

            except Exception as e:
                status.update(label="An error occurred", state="error", expanded=True)
                st.error(f"Error processing audio: {str(e)}")
                st.stop()

        # 2. Display Transcript
        st.subheader("2. Transcript")
        st.info(f'"{result.transcript}"')

        # 3. Display Structured Action Items
        st.subheader("3. Action Items")
        if not result.action_items:
            st.warning("No actionable tasks identified in this recording.")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(result.action_items):
                col = cols[idx % 2]
                with col:
                    # Color indicator for priority
                    priority_lower = item.priority.lower()
                    color = "🔴" if priority_lower == "high" else ("🟡" if priority_lower == "medium" else "🟢")
                    
                    with st.container(border=True):
                        st.markdown(f"### {color} {item.task}")
                        st.markdown(f"**Owner:** `{item.owner or 'Unassigned'}`")
                        st.markdown(f"**Due Date:** `{item.due_date or 'Not specified'}`")
                        st.markdown(f"**Priority:** `{item.priority.capitalize()}`")