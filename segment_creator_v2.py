import asyncio
from playwright.async_api import Page

async def _dismiss_backdrops(page: Page):
    """Utility to clear MUI menus or backdrops that might be blocking clicks."""
    backdrops = page.locator("div[class*='MuiBackdrop-root'], div[id='menu-appbar']")
    if await backdrops.count() > 0:
        print("  -> Dismissing UI backdrop/menu...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

async def create_segments(page: Page, transcript_data: list):
    """
    V2 Segment Creation: Uses the [+] button on the header of the LAST segment 
    to create new blocks, and then fills in the start/end times.
    """
    print(f"\n[CREATE-V2] Starting creation of {len(transcript_data)-1} new segments...")
    
    for idx, seg in enumerate(transcript_data):
        if idx == 0:
            print(f"[CREATE-V2] Updating base segment (0) with {seg['start']} - {seg['end']}")
            await _update_segment_times(page, 0, seg['start'], seg['end'])
            continue
            
        # Target the [+] button. SCOPED to the current segment headers to avoid header-bar collisions.
        # We find the '+' buttons specifically within segment-like rows.
        await _dismiss_backdrops(page)
        
        # We click the [+] button on the LAST available segment to spawn the next one.
        # This ensures we always expand the list sequentially.
        plus_btns = page.locator("div[class*='segment'] button:has-text('+'), div[class*='row'] button:has-text('+')")
        count = await plus_btns.count()
        
        if count > 0:
            last_plus = plus_btns.nth(count - 1)
            print(f"[CREATE-V2] Clicking [+] on segment {count-1} to create segment {idx}...")
            await last_plus.scroll_into_view_if_needed()
            await last_plus.click()
            await page.wait_for_timeout(1500) 
            
            await _update_segment_times(page, idx, seg['start'], seg['end'])
        else:
            print(f"[CREATE-V2] Error: Could not find [+] button in any segment row.")
            break

    print(f"[CREATE-V2] Finished creating all segments.")

async def _update_segment_times(page: Page, idx: int, start_time: str, end_time: str):
    """Surgical time entry handling HH:MM:SS.MS split fields."""
    import re
    start_parts = re.split(r'[:.]', start_time)
    end_parts = re.split(r'[:.]', end_time)
    
    # Locate all segment headers/rows
    segment_rows = page.locator("div[class*='segment'], div[class*='row'], div[class*='Block']")
    row = segment_rows.nth(idx)
    
    # Targeted search: find all indexable inputs within this row
    row_inputs = row.locator("input")
    count = await row_inputs.count()
    
    if count >= 8:
        # Start Time (first 4 inputs)
        for i in range(4):
             await _fill_single(page, row_inputs.nth(i), start_parts[i])
        # End Time (last 4 inputs)
        for i in range(4):
             await _fill_single(page, row_inputs.nth(count - (4-i)), end_parts[i])
        print(f"  -> Segment {idx} fields filled.")
    else:
        # GLOBAL FALLBACK: If row-locating fails, find indexable inputs globally by offset
        print(f"  -> Row {idx} local search failed ({count} inputs). Using Global Offset...")
        # We skip the main header by looking for inputs inside a segment/row container
        all_stage_inputs = page.locator("div[class*='segment'] input, .MuiGrid-item input")
        base = idx * 8
        if await all_stage_inputs.count() >= base + 8:
            for i in range(4):
                 await _fill_single(page, all_stage_inputs.nth(base + i), start_parts[i])
            for i in range(4):
                 await _fill_single(page, all_stage_inputs.nth(base + 4 + i), end_parts[i])
            print(f"  -> Segment {idx} global fields filled.")
        else:
            print(f"  -> Fatal: Could not find inputs for segment {idx}.")

async def _fill_single(page, locator, val):
    """Helper to clear and type into a single sub-input with stable interaction."""
    try:
        await locator.click(click_count=3)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await locator.type(val, delay=10)
    except: pass
        
