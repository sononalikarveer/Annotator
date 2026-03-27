import asyncio
from playwright.async_api import async_playwright
import os

async def debug_ui(url: str):
    user_data_dir = os.path.join(os.getcwd(), "annotic_profile")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url)
        print(f"Waiting 15 seconds for segments to fully render at {url}...")
        await page.wait_for_timeout(15000)
        
        # Take a screenshot to see what we are dealing with!
        screenshot_path = os.path.join(os.getcwd(), "debug_ui_view.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        print("\n--- DEEP INTERActive INSPECTION ---")
        # ... rest of the logic ...
        elements = await page.evaluate("""
            () => {
                const results = [];
                const search = (root) => {
                    const all = root.querySelectorAll('*');
                    all.forEach((el, i) => {
                        const title = (el.title || "").toLowerCase();
                        const aria = (el.getAttribute('aria-label') || "").toLowerCase();
                        const role = (el.getAttribute('role') || "").toLowerCase();
                        const text = el.innerText ? el.innerText.trim().toLowerCase() : "";
                        const tagName = el.tagName.toLowerCase();
                        
                        // Look for anything that might be our target or a button
                        if (title.includes('delete') || aria.includes('delete') || 
                            title.includes('add') || aria.includes('add') ||
                            title.includes('plus') || aria.includes('plus') ||
                            title.includes('insert') || aria.includes('insert') ||
                            tagName === 'button' || role === 'button') {
                            
                            results.push({
                                tag: el.tagName,
                                title: el.title,
                                aria: el.getAttribute('aria-label'),
                                role: role,
                                text: text.slice(0, 30),
                                classes: el.className
                            });
                        }
                        
                        if (el.shadowRoot) search(el.shadowRoot);
                    });
                };
                search(document);
                return results;
            }
        """)
        for el in elements:
             if el['title'] or el['aria']:
                print(f"{el['tag']}: title='{el['title']}' aria='{el['aria']}' role='{el['role']}' text='{el['text']}'")

        await context.close()

if __name__ == "__main__":
    url = "https://annotic.in/#/projects/85/AudioTranscriptionLandingPage/54074"
    asyncio.run(debug_ui(url))
