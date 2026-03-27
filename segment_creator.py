import asyncio
from playwright.async_api import Page

async def _seek_audio(page: Page, time_sec: float):
    """Seek the audio element to a specific time and wait for UI to update."""
    await page.evaluate(f"""() => {{
        const audio = document.querySelector('audio');
        if (audio) {{
            audio.currentTime = {time_sec};
            audio.dispatchEvent(new Event('timeupdate', {{ bubbles: true }}));
            audio.dispatchEvent(new Event('seeked',     {{ bubbles: true }}));
        }}
    }}""")
    # Wait for the playhead rendering to catch up
    await page.wait_for_timeout(500)

async def create_segments(page: Page, transcript_data: list):
    waveform_selector = ".wf-player canvas" 
    
    try:
        await page.wait_for_selector(waveform_selector, timeout=5000)
    except Exception:
        print("Could not find canvas. Pausing.")
        await page.pause()
        
    box = await page.locator(waveform_selector).first.bounding_box()
    if not box: return
        
    # Get total actual duration
    total_duration = await page.evaluate("() => { const a = document.querySelector('audio'); return a ? a.duration : 0; }")
    if not total_duration or total_duration == 0:
        total_duration = float(transcript_data[-1].get("raw_end", 0.0)) + 5.0
        
    full_width = await page.evaluate('document.querySelector(".wf-player canvas").scrollWidth')
    pixels_per_second = full_width / total_duration
        
    for idx, seg in enumerate(transcript_data):
        start_sec = seg["raw_start"]
        end_sec = seg["raw_end"]
        
        if idx == 0:
            # Segment 0 was preserved by the deletion process! We don't drag for it.
            print(f"Skipping drag for index 0 to preserve the retained base segment.")
            continue
            
        print(f"Seeking playhead to {start_sec:.2f}s for Segment {idx + 1}")
        await _seek_audio(page, start_sec)
        
        # The native DOM query for '.wf-cursor' frequently returns 0.0 due to 
        # Annotic nesting the element within a shadow DOM / iframe context.
        # Instead, we exclusively use pure mathematical relative coordinates!
        playhead_x = box['x'] + (start_sec * pixels_per_second)

        # Drag width based on scroll ratio, not viewport width
        drag_width_px = (end_sec - start_sec) * pixels_per_second
        
        drag_from_x = playhead_x
        drag_to_x = playhead_x + drag_width_px
        drag_y = box['y'] + (box['height'] / 2)
        
        # Drag LEFT -> RIGHT
        print(f"Dragging segment {idx + 1} exactly from playhead {drag_from_x:.1f} to {drag_to_x:.1f}")
        
        # KEY BUG FIX: We must pause 80ms between every physical mouse interaction. 
        # Otherwise Playwright fires too fast and the React Javascript single-thread crashes!
        await page.mouse.move(drag_from_x, drag_y)
        await page.wait_for_timeout(80)
        
        await page.mouse.down()
        await page.wait_for_timeout(80)
        
        # Calculate steps realistically (approx 5px per step) to simulate humans
        steps = max(10, int(drag_width_px / 5))
        await page.mouse.move(drag_to_x, drag_y, steps=steps)
        await page.wait_for_timeout(80)
        
        await page.mouse.up()
        await page.wait_for_timeout(500)

    print(f"Finished dragging all {len(transcript_data)} segments!")
