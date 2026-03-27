import asyncio
from playwright.async_api import Page

async def delete_existing_segments(page: Page):
    """
    Refined Delete: Since the 'Delete' button may be hidden until hover (confirmed by screenshot),
    we use a hover strategy on the segment row/index and then look for the trash icon.
    """
    print("\n[DELETE-V2] Starting refined hover-delete flow...")
    await page.wait_for_timeout(2000)

    # Selector for the segment index circles (1, 2, 3...)
    # Finding elements that contain numbers in a span inside a segment div
    INDEX_SELECTOR = "div[class*='segment'] span[class*='index'], .segmentIndex, [class*='blockNumber']"
    
    # Selector for the trash button that appears after hover
    TRASH_SELECTOR = "button[title*='elete'], button[aria-label*='elete'], button:has(svg[data-testid*='Delete'])"

    while True:
        # Re-query indices every time (React removes nodes)
        indices = page.locator(INDEX_SELECTOR)
        count = await indices.count()
        
        if count <= 1:
            print("[DELETE-V2] Only base block (index 0) remains. Done.")
            break
            
        print(f"[DELETE-V2] Deleting block {count-1}...")
        
        # 1. Hover over the last segment's number circle
        last_index = indices.nth(count - 1)
        try:
            await last_index.scroll_into_view_if_needed()
            await last_index.hover()
            await page.wait_for_timeout(1000) # Give UI time to reveal button
            
            # 2. Look for the delete button specifically
            delete_btn = page.locator(TRASH_SELECTOR).first
            
            if await delete_btn.count() > 0:
                await delete_btn.click()
                await page.wait_for_timeout(1000)
            else:
                print(f"[DELETE-V2] Error: Delete button did NOT appear after hover on index {count-1}.")
                # Fallback: maybe the row itself needs hover
                await last_index.locator("..").hover()
                await page.wait_for_timeout(1000)
                delete_btn = page.locator(TRASH_SELECTOR).first
                if await delete_btn.count() > 0:
                    await delete_btn.click()
                    await page.wait_for_timeout(1000)
                else:
                    print("[DELETE-V2] Fallback hover also failed. Stopping to avoid infinite loop.")
                    break
        except Exception as e:
            print(f"[DELETE-V2] Exception during hover/delete: {e}")
            break

    print(f"[DELETE-V2] Deletion cycle complete.")
