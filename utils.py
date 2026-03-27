import asyncio
from playwright.async_api import Page

async def save_and_continue(page: Page):
    """
    Clicks the necessary save and Next button on the Annotic website.
    """
    try:
        # Generic button guess for "Save" or "Next" or "Submit"
        submit_btn = page.locator('button:has-text("Save"), button:has-text("Submit"), button:has-text("Save & Next")').first
        if await submit_btn.count() > 0:
            print("Clicking save and continue button...")
            await submit_btn.click()
            await page.wait_for_load_state('networkidle')
            print("Successfully submitted the annotation task.")
        else:
            print("Could not find a submit button on this page.")
            
    except Exception as e:
        print(f"An error occurred while saving: {e}")
