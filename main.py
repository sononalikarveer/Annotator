import warnings
import os
import sys

# 1. FORCED PATH REPAIR: Explicitly point to the validated FFmpeg binary folder
# This bypasses the corrupted Registry entry that was causing "WinError 3".
VALID_FFMPEG_DIR = r"C:\Users\vrnre\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build-shared\bin"

cleaned_paths = [VALID_FFMPEG_DIR] # Force-start with the known good one!
for p in os.environ.get("PATH", "").split(os.pathsep):
    clean_p = p.replace("\n", "").replace("\r", "").strip().strip('"')
    if clean_p and os.path.isdir(clean_p) and clean_p not in cleaned_paths:
        cleaned_paths.append(clean_p)
os.environ["PATH"] = os.pathsep.join(cleaned_paths)

# 2. SILENCE WARNINGS: Suppress the massive torchcodec DLL initialization tracebacks
warnings.filterwarnings("ignore", category=UserWarning, module=".*torchcodec.*")
warnings.filterwarnings("ignore", message=".*torchcodec is not installed correctly.*")

import asyncio
from playwright.async_api import async_playwright

from audio_extractor import extract_audio
from transcriber import transcribe_audio
from segment_creator_v2 import create_segments
from segment_deleter_v2 import delete_existing_segments
from text_filler import fill_text
from utils import save_and_continue

async def run_annotation_bot(url: str):
    print(f"Starting bot for URL: {url}")
    
    # Use a persistent profile folder locally so we only log in ONCE.
    user_data_dir = os.path.join(os.getcwd(), "annotic_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # Instead of launching a clean incognito-like browser, we launch a persistent profile
        # This acts like a real saved Chrome profile where your login is remembered.
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome", # Forces Windows to use ACTUAL Google Chrome instead of Playwright Chromium!
            args=['--disable-blink-features=AutomationControlled'] # Helps prevent script blocking
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto(url)
        
        # Step 1: Extract Audio
        print("Extracting audio from webpage...")
        audio_file_path = await extract_audio(page)
        print(f"Audio saved to {audio_file_path}")
        
        # Step 2: Transcribe with WhisperX and apply custom rules
        print("Transcribing audio and applying rules...")
        # Path to local rules or dynamically passed
        transcript_data = transcribe_audio(audio_file_path)
        print(f"Transcription complete. Segments found: {len(transcript_data)}")
        
        # Step 3: Delete existing segments (if any)
        print("Deleting pre-existing layout segments...")
        await delete_existing_segments(page)
        
        # Step 4: Create segments on the canvas based on timestamps
        print("Creating segments on the waveform...")
        await create_segments(page, transcript_data)
        
        # Step 5: Fill the text blocks based on transcript text + tagging rules
        print("Filling text blocks...")
        await fill_text(page, transcript_data)
        
        # Step 5: Save and continue
        print("Saving and continuing...")
        await save_and_continue(page)
        
        # Wait indefinitely for you to review and close the browser manually!
        print("Bot has finished! The browser will stay open until you close the terminal or script.")
        await page.pause()
        
        # Or alternatively:
        # import asyncio
        # await asyncio.Future()  # This will pause the script forever and keep the window open!

        await context.close()
        print("Successfully processed the URL!")

def main():
    # Prompting for a single URL or reading from a list
    sample_urls = [
        "https://annotic.in/#/projects/85/AudioTranscriptionLandingPage/54074"
    ]
    
    for url in sample_urls:
        asyncio.run(run_annotation_bot(url))

if __name__ == "__main__":
    main()
