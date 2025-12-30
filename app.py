import streamlit as st
import os
from dotenv import load_dotenv
from utils import get_video_transcript, generate_summary, get_video_id
from tenacity import RetryError

# Load environment variables
load_dotenv()

# Page Configuration
st.set_page_config(page_title="AI YouTube Video Summarizer", page_icon="📺", layout="wide")

st.title("AI YouTube Video Summarizer")

# Main Interface
url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "last_url" not in st.session_state:
    st.session_state.last_url = None

if url and url != st.session_state.last_url:
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("Google API Key is missing. Please add it to your .env file.")
    else:
        with st.spinner("Fetching transcript and generating summary..."):
            try:
                # Get Transcript
                transcript = get_video_transcript(url)
                st.session_state.transcript = transcript
                
                # Get Summary
                summary = generate_summary(transcript)
                st.session_state.summary = summary
                
                # Update last processed URL
                st.session_state.last_url = url
                
            except RetryError:
                st.error("API Quota Exceeded. Please try again later or use a shorter video.")
            except Exception as e:
                st.error(f"Error: {e}")

# Display Results
if st.session_state.summary:
    st.subheader("Video Content")
    if url:
        st.video(url)
    st.markdown(st.session_state.summary)
