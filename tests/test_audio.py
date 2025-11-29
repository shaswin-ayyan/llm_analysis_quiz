import asyncio
from app.agents.tools import transcribe_audio_tool
from app.config import settings

async def test_audio():
    print("Testing transcribe_audio_tool with Gemini...")
    
    if not settings.GEMINI_API_KEY:
        print("SKIPPING: GEMINI_API_KEY not found.")
        return

    # Use a reliable short audio sample (WAV)
    # This one is from Mozilla Common Voice sample or similar public domain
    url = "https://www2.cs.uic.edu/~i101/SoundFiles/BabyElephantWalk60.wav"
    # Actually, let's use a very standard one.
    url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    # Gemini supports OGG.
    # Or a speech sample:
    url = "https://storage.googleapis.com/generativeai-downloads/data/Sherlock_Jr_FullMovie.mp3" # Too big
    
    # Let's use a small sample hosted on a reliable CDN or repo
    url = "https://github.com/rafaelpadilla/DeepLearning-VAD/raw/master/audio/1.wav" # This one might be 404 too
    
    # Let's try the one that worked in my browser:
    url = "https://www.signalogic.com/melp/EngSamples/Orig/male.wav"

    print(f"Downloading and transcribing: {url}")
    result = await transcribe_audio_tool({"url": url}, None)
    
    if isinstance(result, dict) and "text" in result:
        print("SUCCESS: Transcribed audio.")
        print(f"Text: {result['text']}")
    else:
        print(f"FAILURE: {result}")

if __name__ == "__main__":
    asyncio.run(test_audio())
