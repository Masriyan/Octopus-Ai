"""
Octopus AI — Web Tentacle 🌐
Fetch and parse web pages.
"""
import httpx
from bs4 import BeautifulSoup
from tools import BaseTool


class WebTool(BaseTool):
    name = "web_browse"
    description = "Fetch a web page URL and extract its text content. Useful for reading documentation, articles, API responses, or any web content."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch"
            },
            "extract_links": {
                "type": "boolean",
                "description": "Whether to also extract all links from the page (default: false)"
            }
        },
        "required": ["url"]
    }

    async def execute(self, url: str, extract_links: bool = False, **kwargs) -> dict:
        try:
            headers = {
                "User-Agent": "OctopusAI/1.0 (Web Research Bot)"
            }
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                response = await client.get(url, headers=headers)

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "url": url
                }

            content_type = response.headers.get("content-type", "")

            # Handle JSON responses
            if "application/json" in content_type:
                return {
                    "status": "success",
                    "url": url,
                    "content_type": "json",
                    "content": response.text[:15000]
                }

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            title = soup.title.string if soup.title else ""
            text = soup.get_text(separator="\n", strip=True)
            # Collapse whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)[:15000]

            result = {
                "status": "success",
                "url": url,
                "title": title,
                "content": text,
                "content_type": "html"
            }

            if extract_links:
                links = []
                for a in soup.find_all("a", href=True)[:50]:
                    href = a["href"]
                    link_text = a.get_text(strip=True)
                    if href.startswith("http"):
                        links.append({"text": link_text, "url": href})
                result["links"] = links

            return result

        except httpx.TimeoutException:
            return {"status": "error", "error": "Request timed out", "url": url}
        except Exception as e:
            return {"status": "error", "error": str(e), "url": url}
