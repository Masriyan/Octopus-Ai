"""
Octopus AI — Web Tentacle 🌐
Actively browse, interact with, and parse web pages using Playwright.
"""
from tools import BaseTool

try:
    from playwright.async_api import async_playwright
    import markdownify
    from bs4 import BeautifulSoup
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    import httpx
    # Fallback to basic if playwright is somehow missing


class WebTool(BaseTool):
    name = "web_browse"
    description = "Actively browse the web. Can navigate to URLs, click elements, fill text, and wait for elements. Returns the rendered page as Markdown."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch/navigate to"
            },
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "fill", "press", "screenshot"],
                "description": "Action to perform (default: navigate)."
            },
            "selector": {
                "type": "string",
                "description": "CSS/XPath selector for click/fill/press actions."
            },
            "text": {
                "type": "string",
                "description": "Text to type if action is 'fill', or key if action is 'press'."
            },
            "wait_for": {
                "type": "string",
                "description": "Optional selector to wait for before returning the page."
            }
        },
        "required": ["url"]
    }

    async def execute(self, url: str, action: str = "navigate", selector: str = None, text: str = None, wait_for: str = None, extract_links: bool = False, **kwargs) -> dict:
        if not HAS_PLAYWRIGHT:
            return await self._fallback_fetch(url)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Setting block for media/images can speed up rendering 
                # but we'll try to load everything normally
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OctopusAI"
                )
                page = await context.new_page()

                try:
                    # Always navigate first if URL is provided and not already on it
                    current_url = page.url
                    if current_url != url and url and url != "about:blank":
                        # Playwright might timeout on infinite loading pages, catch it gracefully
                        try:
                            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        except Exception as nav_e:
                            if "Timeout" not in str(nav_e):
                                raise nav_e

                    # Perform specific action
                    if action == "click" and selector:
                        await page.click(selector, timeout=5000)
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=5000)
                        except: pass
                    elif action == "fill" and selector and text:
                        await page.fill(selector, text, timeout=5000)
                    elif action == "press" and selector and text:
                        await page.press(selector, text, timeout=5000)
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=5000)
                        except: pass

                    if wait_for:
                        await page.wait_for_selector(wait_for, timeout=5000)
                        
                    # Handle Screenshot
                    screenshot_b64 = None
                    if action == "screenshot":
                        screenshot_bytes = await page.screenshot(type='jpeg', quality=50)
                        import base64
                        screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

                    # Extract Content
                    title = await page.title()
                    html_content = await page.content()

                except Exception as e:
                    await browser.close()
                    return {"status": "error", "error": f"Playwright Action Error: {e}", "url": url}

                await browser.close()

            # Parse with BS4 to clean up script/style tags
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract links if requested
            links = []
            if extract_links:
                for a in soup.find_all("a", href=True)[:50]:
                    href = a["href"]
                    link_text = a.get_text(strip=True)
                    if href.startswith("http"):
                        links.append({"text": link_text, "url": href})
                        
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                tag.decompose()

            # Convert to Markdown
            md_text = markdownify.markdownify(str(soup), heading_style="ATX")
            
            # Collapse excess whitespace
            lines = [line.strip() for line in md_text.splitlines() if line.strip()]
            final_text = "\n".join(lines)[:20000] # Increased limit for rich pages

            result = {
                "status": "success",
                "url": url,
                "title": title,
                "content": final_text,
                "action_executed": action
            }

            if extract_links:
                result["links"] = links

            if screenshot_b64:
                result["screenshot_base64"] = screenshot_b64

            return result

        except Exception as e:
            return {"status": "error", "error": str(e), "url": url}

    async def _fallback_fetch(self, url: str) -> dict:
        """Original HTTPX logic as fallback."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15, verify=False) as client:
                response = await client.get(url)
            return {
                "status": "success",
                "content": response.text[:10000],
                "note": "Playwright unavailable, fallback to HTTPX."
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
