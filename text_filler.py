import asyncio
from playwright.async_api import Page

async def fill_text(page: Page, transcript_data: list):
    """
    Locates the generated text areas for every segment that was created,
    and fills them with the transcribed data.
    """
    # NOTE: The actual css selectors depend on the exact DOM of Annotic's platform.
    # Use the bulletproof `#subTitleContainer` locator pattern just like we do in segment_deleter!
    segment_rows = page.locator("div[id^='sub_']")
    count = await segment_rows.count()
    
    print(f"Found {count} segment rows to fill. Target data length: {len(transcript_data)}")
    
    with open("filled_text.log", "w", encoding="utf-8") as log_file:
        log_file.write(f"--- ANNOTIC TEXT FILL LOG ---\n")
        log_file.write(f"Segment Rows found on page: {count}\n")
        log_file.write(f"Total Transcript segments available: {len(transcript_data)}\n\n")
        
        for i in range(min(count, len(transcript_data))):
            text_to_fill = transcript_data[i]["text"]
            
            # Scope to the specific segment block
            segment_el = segment_rows.nth(i)
            
            # Click the segment row to expand/activate it just in case textareas are hidden!
            await segment_el.click()
            await asyncio.sleep(0.4)
            
            # Wait for textarea inside this specific expanded segment
            textarea = segment_el.locator("textarea")
            try:
                await textarea.wait_for(state='visible', timeout=10000)
            except Exception:
                # Fallback: Maybe click a header to toggle? 
                print(f"Segment {i} textarea still hidden. Trying fallback layout click.")
                await segment_el.locator("div").first.click()
                await asyncio.sleep(0.4)
                await textarea.wait_for(state='visible', timeout=8000)
            
            # Click into the block to ensure focus, clear, and fill
            await textarea.click()
            await textarea.fill("")
            await textarea.fill(text_to_fill)
            
            # write confirmation to log file
            log_file.write(f"Segment {i + 1} | Time: {transcript_data[i].get('start')} - {transcript_data[i].get('end')}\n")
            log_file.write(f"Filled Text:\n{text_to_fill}\n")
            log_file.write("-" * 40 + "\n")
            
            print(f"Filled segment {i + 1} with text: {text_to_fill[:20]}...")
            await asyncio.sleep(0.2)
