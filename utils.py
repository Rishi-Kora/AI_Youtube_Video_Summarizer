import os
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import Document
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted

# Retry configuration
# Wait exponential: 4s, 8s, 16s, ... up to 60s. Stop after 5 attempts.
RETRY_CONFIG = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=2, min=4, max=60),
    "retry": retry_if_exception_type(ResourceExhausted)
}


import google.generativeai as genai

# Monkeypatch to fix max_retries issue with langchain-google-genai vs google-generativeai
# Confirmed working via debug_patch.py
_original_generate_content = genai.GenerativeModel.generate_content

def _generate_content_patched(self, *args, **kwargs):
    kwargs.pop('max_retries', None)
    return _original_generate_content(self, *args, **kwargs)

genai.GenerativeModel.generate_content = _generate_content_patched

# Initialize LLM
# Using Gemini-2.0-flash-lite as it is efficient and we handle retries externally
def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    return ChatGoogleGenerativeAI(model="gemma-3-12b-it", google_api_key=api_key, temperature=0.7)

def get_video_id(url: str) -> str:
    """Extracts video ID from a YouTube URL."""
    try:
        query = urlparse(url)
        if query.hostname == 'youtu.be':
            return query.path[1:]
        if query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch':
                p = parse_qs(query.query)
                return p['v'][0]
            if query.path[:7] == '/embed/':
                return query.path.split('/')[2]
            if query.path[:3] == '/v/':
                return query.path.split('/')[2]
    except Exception:
        pass
    return None

def get_video_transcript(url: str) -> str:
    """Retrieves the transcript of a YouTube video."""
    video_id = get_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    
    try:
        # Use valid instance-based API for installed youtube-transcript-api 1.2.3
        api = YouTubeTranscriptApi()
        transcripts = api.list(video_id)
        
        # Try to find English transcript (manual or generated)
        # This will return a Transcript object
        transcript = transcripts.find_transcript(['en', 'en-US', 'en-GB'])
        
        # Fetch the actual data
        # Returns a list of FetchedTranscriptSnippet objects
        data = transcript.fetch()
        
        # Combine text
        # Access .text attribute of the snippet object
        full_text = " ".join([snippet.text for snippet in data])
        
        # Truncate to avoid token limits (approx 5-6k tokens)
        if len(full_text) > 20000:
            full_text = full_text[:20000] + "... [Truncated to save tokens]"
            
        return full_text
        
    except Exception as e:
        raise RuntimeError(f"Failed to load transcript: {str(e)}")

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60), retry=retry_if_exception_type(ResourceExhausted))
def run_chain_with_retry(chain, inputs):
    """Helper to run a chain with retry logic for rate limits."""
    return chain.run(inputs)

def generate_summary(transcript: str) -> str:
    """Generates a structured summary using LLMChain."""
    llm = get_llm()
    
    template = """
    You are a helpful assistant that summarizes YouTube videos.
    Here is the transcript of a video:
    
    "{transcript}"
    
    Analyze the content to determine if this is a COMPARISON video or a SINGLE TOPIC video.
    
    CRITICAL INSTRUCTION: Analyze the video type.
    - IF it is a COMPARISON video: Output ONLY a Markdown comparison table (rows=features, cols=items).
    - IF it is a SINGLE TOPIC video: Output ONLY a concise "Gist" paragraph of the main message.
    
    Do NOT output any labels like "If COMPARISON" or "Analysis". Just output the Table or the Text.
    """
    
    prompt = PromptTemplate(template=template, input_variables=["transcript"])
    chain = LLMChain(llm=llm, prompt=prompt)
    
    # Run with retry
    return run_chain_with_retry(chain, {"transcript": transcript})

def answer_question(transcript: str, question: str, chat_history: str = "") -> str:
    """Answers a question about the video based on the transcript."""
    llm = get_llm()
    
    template = """
    You are a helpful assistant. You have been provided with the transcript of a video.
    
    Video Transcript:
    "{transcript}"
    
    Chat History:
    {chat_history}
    
    User Question: {question}
    
    Answer the user's question based strictly on the video content provided above.
    """
    
    prompt = PromptTemplate(template=template, input_variables=["transcript", "question", "chat_history"])
    chain = LLMChain(llm=llm, prompt=prompt)
    
    inputs = {
        "transcript": transcript,
        "question": question,
        "chat_history": chat_history
    }
    return run_chain_with_retry(chain, inputs)
