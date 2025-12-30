# AI YouTube Video Summarizer

## Problem Statement

Users find it time-consuming and inefficient to watch long-form YouTube videos solely to extract key insights, actionable comparisons, or summaries. Standard summarization tools often treat all videos the same, failing to distinguish between **comparative content** (e.g., "Pixel 9 vs iPhone 16") and **educational/single-topic content** (e.g., "History of Rome"), leading to unstructured or generic outputs that are hard to read.

## Solution Overview

This project provides an intelligent YouTube video summarizer that automatically detects the video type and formats the output accordingly:

- **Comparison videos**: Outputs a clean Markdown table for easy scanning
- **Single-topic videos**: Provides a concise paragraph summary

The solution consists of two Python files:

1. `utils.py` - Core logic for fetching data and AI processing
2. `app.py` - Streamlit frontend for user interaction

## Architecture

### utils.py

This file handles the **heavy lifting**: fetching data, talking to the AI, and ensuring reliability.

#### Key Features

**Robustness (Retries & Patches)**
- Implements custom `RETRY_CONFIG` using the `tenacity` library
- Automatically retries on Google API failures (e.g., "Resource Exhausted")
- Uses exponential backoff (waits 4s, then 8s, etc.)
- Includes a **monkeypatch** (`_generate_content_patched`) for the `google.generativeai` library to fix a known bug preventing retries from working correctly

**Transcript Fetching (`get_video_transcript`)**
1. Uses `youtube_transcript_api` to download subtitles
2. Includes a check to truncate extremely long transcripts (over 20,000 chars) to prevent overwhelming the LLM

**Smart Summarization (`generate_summary`)**
1. Uses **LangChain** and Google's **Gemini** model (gemma-3-12b-it or similar)
2. The prompt at line 99 is the most critical part - it instructs the AI to **classify** the video type and format the output appropriately

### Output Modes

#### 1. Comparison Mode
For videos comparing two or more items (e.g., "iPhone 16 vs Pixel 9"):

**Output Format**: Clean Markdown Table

| Feature | iPhone 16 | Google Pixel 9 |
|---------|-----------|----------------|
| **Camera** | 48MP Fusion | 50MP Wide |
| **Battery** | 20 hours video | 24+ hours |
| **Price** | $799 | $699 |

**Why**: Makes it easy to scan differences instantly.

#### 2. Single Topic Mode
For educational or narrative videos (e.g., "The History of Rome"):

**Output Format**: Concise paragraph summary

**Example**:
> **Summary**: This video provides a comprehensive overview of the Roman Empire's rise, highlighting the transition from Republic to Empire under Augustus. It covers key military reforms, the Pax Romana, and the eventual administrative challenges that led to its decline.

**Why**: Provides a quick summary of the main narrative without unnecessary formatting.

### app.py

This file is the **frontend entry point**, built using **Streamlit**. It handles user interaction and display logic.

#### Key Features

1. **Session Management**: Uses `st.session_state` to store the transcript, summary, and `last_url`. This ensures that when you interact with the app (or if Streamlit reruns the script), you don't lose the summary you just generated.

2. **Input & Validation**:
   - Takes a YouTube URL as input
   - Checks if the `GOOGLE_API_KEY` is set in your `.env` file before proceeding

## Workflow Diagram

<img width="1821" height="1446" alt="image" src="https://github.com/user-attachments/assets/d0dbe9de-c728-42e8-87d6-b696035eeb86" />


## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-summarizer.git
cd youtube-summarizer

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

## Usage

```bash
# Run the Streamlit app
streamlit run app.py
```

1. Open your browser to the provided local URL
2. Paste a YouTube video URL
3. Click "Summarize"
4. View the formatted output based on video type

## Requirements

- Python 3.8+
- streamlit
- langchain
- google-generativeai
- youtube-transcript-api
- tenacity
- python-dotenv

## License

This project is licensed under the **MIT License**. See [LICENSE](./LICENSE) for details.

**NOTE:** Use your own **API Key** and **Model.**
