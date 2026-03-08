import pytest
from tools.web_tool import WebTool

@pytest.fixture
def web_tool():
    return WebTool()

@pytest.mark.asyncio
async def test_web_browse_success(web_tool):
    # Use a reliable, fast, plain-text-ish site for testing
    url = "https://example.com"
    result = await web_tool.execute(url=url)
    
    assert result["status"] == "success"
    assert "Example Domain" in result["title"]
    assert "This domain is for use in documentation examples" in result["content"]

@pytest.mark.asyncio
async def test_web_browse_invalid_url(web_tool):
    url = "http://this-does-not-exist-123456789.com"
    result = await web_tool.execute(url=url)
    
    assert result["status"] == "error"
    assert "error" in result

@pytest.mark.asyncio
async def test_web_browse_extract_links(web_tool):
    url = "https://example.com"
    result = await web_tool.execute(url=url, extract_links=True)
    
    assert result["status"] == "success"
    assert "links" in result
    assert len(result["links"]) > 0
    assert result["links"][0]["url"].startswith("http")
