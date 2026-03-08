import asyncio
from tools.web_tool import WebTool

async def test():
    tool = WebTool()
    print("Fetching Example...")
    res = await tool.execute(url="https://example.com")
    print(res["content"][:200])
    
if __name__ == "__main__":
    asyncio.run(test())
