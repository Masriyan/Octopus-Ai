import os
import pytest
from tools.file_tool import FileTool

@pytest.fixture
def file_tool():
    return FileTool()

@pytest.fixture
def temp_test_dir(tmp_path):
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()
    return test_dir

@pytest.mark.asyncio
async def test_file_write_and_read(file_tool, temp_test_dir):
    test_file = temp_test_dir / "test.txt"
    test_content = "Hello, Octopus AI!"
    
    # Test Write
    write_result = await file_tool.execute(
        operation="write",
        path=str(test_file),
        content=test_content
    )
    assert write_result["status"] == "success"
    assert os.path.exists(test_file)
    
    # Test Read
    read_result = await file_tool.execute(
        operation="read",
        path=str(test_file)
    )
    assert read_result["status"] == "success"
    assert read_result["content"] == test_content

@pytest.mark.asyncio
async def test_file_edit_and_read_lines(file_tool, temp_test_dir):
    test_file = temp_test_dir / "test_edit.txt"
    test_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    
    # Test Write
    await file_tool.execute(
        operation="write",
        path=str(test_file),
        content=test_content
    )
    
    # Test Edit
    edit_result = await file_tool.execute(
        operation="edit",
        path=str(test_file),
        replace_text="Line 3",
        content="Edited Line 3"
    )
    assert edit_result["status"] == "success"
    
    # Test Read Lines
    read_lines_result = await file_tool.execute(
        operation="read_lines",
        path=str(test_file),
        start_line=2,
        end_line=4
    )
    assert read_lines_result["status"] == "success"
    # Lines 2, 3(edited), 4
    assert read_lines_result["content"] == "Line 2\nEdited Line 3\nLine 4\n"
    assert read_lines_result["total_lines"] == 5

@pytest.mark.asyncio
async def test_file_edit_not_found(file_tool, temp_test_dir):
    test_file = temp_test_dir / "test_edit_fail.txt"
    await file_tool.execute(
        operation="write",
        path=str(test_file),
        content="Only this line"
    )
    
    edit_result = await file_tool.execute(
        operation="edit",
        path=str(test_file),
        replace_text="Nonexistent text",
        content="New text"
    )
    assert edit_result["status"] == "error"
    assert "not found in file" in edit_result["error"].lower()

@pytest.mark.asyncio
async def test_file_list_and_info(file_tool, temp_test_dir):
    # Create a couple of files
    (temp_test_dir / "file1.txt").write_text("1")
    (temp_test_dir / "file2.txt").write_text("2")
    (temp_test_dir / "subdir").mkdir()
    
    # Test List
    list_result = await file_tool.execute(
        operation="list",
        path=str(temp_test_dir)
    )
    assert list_result["status"] == "success"
    assert len(list_result["entries"]) == 3 # 2 files + 1 dir
    
    # Test Info
    info_result = await file_tool.execute(
        operation="info",
        path=str(temp_test_dir / "file1.txt")
    )
    assert info_result["status"] == "success"
    assert info_result["type"] == "file"
    assert "size" in info_result

@pytest.mark.asyncio
async def test_file_read_not_found(file_tool, temp_test_dir):
    result = await file_tool.execute(
        operation="read",
        path=str(temp_test_dir / "nonexistent.txt")
    )
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
