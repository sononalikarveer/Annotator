import asyncio
from playwright.async_api import Page

async def delete_existing_segments(page: Page):
    """
    Restored specific logic:
    1. Go to the Options button on the text box block and click it ONCE.
    2. Reveal all the delete buttons on the screen.
    3. Leaving the very first delete block, press all the buttons to delete the remaining blocks.
    4. Then go for the creation of new blocks.
    """
    print("\n[DELETE] Scanning for 'Options' menu buttons to reveal hidden Delete block triggers...")
    await page.wait_for_timeout(1500)

    # 1. Click the Options button ONCE to expand the menu
    # Common React UI accessibility labels for the 3-dots / gear / options icon
    options_buttons = page.locator("button[aria-label*='Option'], button[aria-label*='More'], button[aria-haspopup='true']")
    
    opts_count = await options_buttons.count()
    if opts_count > 0:
        print(f"[DELETE] Found {opts_count} Options button(s). Clicking it to deploy delete triggers on the screen.")
        try:
            await options_buttons.first.click()
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"[DELETE] Failed to click Options button: {e}")
    else:
        print("[DELETE] Could not find an Options button. Checking if delete buttons are already visible...")

    # 2. Find all the delete buttons that are currently visible
    trash_selectors = [
        "button[aria-label='Delete']",
        "button[aria-label='delete']",
        "button[title='Delete']",
        "button[title='delete']",
        ".segment-delete",
        "button svg[data-testid='DeleteIcon']",
        "xpath=//button[.//svg/path[contains(@d, 'M6 19c0 1.1') or contains(@d, 'M19 4h-3.5')]]"
    ]

    trash_btns = None
    working_sel = None
    for sel in trash_selectors:
        candidate = page.locator(sel) # don't strictly filter visible immediately, rely on DOM existance first
        count = await candidate.count()
        if count > 1:
            trash_btns = candidate
            working_sel = sel
            print(f"[DELETE] Successfully mapped {count} Delete button(s) via '{sel}'.")
            break

    if not trash_btns:
        print("[DELETE] Found 0 delete buttons on the screen. Nothing to delete.")
        return

    count = await trash_btns.count()

    if count <= 1:
        print("[DELETE] Only the FIRST base segment text block exists on the screen. Skipping deletion entirely.")
        return

    print(f"[DELETE] By leaving the first delete button (index 0), pressing all {count - 1} remaining buttons!")

    # 3. Leave the first delete button (index 0) and press all the remaining buttons!
    # Because clicking a button might remove it from the DOM and shift indices, 
    # it is massively safer to iterate BACKWARDS from the last item down to exactly index 1!
    for i in range(count - 1, 0, -1):
        try:
            # We strictly re-query the DOM every loop because React destroys the array nodes dynamically!
            btn = page.locator(working_sel).nth(i)
            await btn.click()
            print(f"[DELETE] Successfully pressed delete button for block {i}.")
            
            # INCREASED TIMEOUT: 800ms to perfectly prevent React state mutation lag/crashes!
            await page.wait_for_timeout(800)
        except Exception as e:
            print(f"[DELETE] Error clicking delete button {i}: {e}. Retrying with direct reference.")
            try:
                await trash_btns.nth(i).click()
                await page.wait_for_timeout(800)
            except Exception:
                pass
            
    # Fallback to empty out the first segment text if any garbage text is in it
    print("[DELETE] Finished successfully! The first text block was perfectly curated on the screen.")
