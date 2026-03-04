"""
Octopus AI — Search Tentacle 🔍
Search the web using DuckDuckGo.
"""
from tools import BaseTool


class SearchTool(BaseTool):
    name = "search_web"
    description = "Search the web using DuckDuckGo. Returns a list of results with titles, URLs, and snippets. Useful for finding information, documentation, or answers."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5, max: 10)"
            }
        },
        "required": ["query"]
    }

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> dict:
        try:
            from duckduckgo_search import DDGS

            max_results = min(max_results, 10)

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    })

            return {
                "status": "success",
                "query": query,
                "results": results,
                "count": len(results)
            }

        except ImportError:
            return {
                "status": "error",
                "error": "duckduckgo-search package not installed. Run: pip install duckduckgo-search"
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "query": query}
