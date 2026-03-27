import asyncio
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
import urllib.request
import os

async def extract_audio(page: Page, save_dir: str = "downloads") -> str:
    """
    Waits for the web page to load the audio. Handles login screens by pausing if needed.
    """
    os.makedirs(save_dir, exist_ok=True)
    audio_path = os.path.join(save_dir, "current_task_audio.wav")
    
    print("Checking if we need to log in first. Please log in if prompted in the browser UI...")
    # Give user a chance to log in if they aren't already. 
    # We will wait for an audio element to appear on the DOM.
    try:
        print("Waiting for <audio> element to appear on the page (timeout 60s)...")
        await page.wait_for_selector("audio", timeout=60000)
        audio_url = await page.get_attribute("audio", "src")
        
        if not audio_url:
            print("Audio tag found but src is empty. Will wait for a network request.")
            raise PlaywrightTimeoutError("No src in audio tag")
            
        print(f"Found audio URL from DOM: {audio_url}")
        
    except PlaywrightTimeoutError:
        print("Falling back to network interception...")
        try:
            async with page.expect_response(lambda response: '.wav' in response.url or '.mp3' in response.url, timeout=30000) as response_info:
                response = await response_info.value
                audio_url = response.url
                print(f"Captured audio URL from network: {audio_url}")
        except PlaywrightTimeoutError:
            print("Failed to find audio. The page might require you to interact, click play, or login.")
            print("Pausing execution so you can manually inspect the page...")
            await page.pause()
            
            # After resume, try one more time to get audio tag
            audio_url = await page.get_attribute("audio", "src")
            if not audio_url:
                raise Exception("Could not retrieve audio URL even after manual pause.")
            
    print("Downloading audio file...")
    # Handle possible blob or relative URLs:
    if audio_url.startswith("blob:"):
        print("Audio is a blob URL. Executing JS to download blob...")
        script = f"""
        async () => {{
            const response = await fetch('{audio_url}');
            const blob = await response.blob();
            return new Promise((resolve, reject) => {{
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            }});
        }}
        """
        data_url = await page.evaluate(script)
        import base64
        header, encoded = data_url.split(",", 1)
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(encoded))
    else:
        # Handle relative URL
        if not audio_url.startswith("http"):
            # Construct absolute
            base_url = page.url
            if audio_url.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                audio_url = f"{parsed.scheme}://{parsed.netloc}{audio_url}"
            else:
                audio_url = f"{base_url.rsplit('/', 1)[0]}/{audio_url}"
                
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                urllib.request.urlretrieve(audio_url, audio_path)
                break
            except Exception as e:
                print(f"Network download attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to download audio after {max_retries} attempts. Please check your internet connection.")
                time.sleep(3)
    
    return audio_path
