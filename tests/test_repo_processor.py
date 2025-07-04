from pathlib import Path
import pytest
import sys
sys.path.append('..')

from repo_processor import LocalRepoProcessor

@pytest.fixture
def processor():
    """Returns an instance of LocalRepoProcessor."""
    return LocalRepoProcessor()

def test_should_process_file_valid(processor):
    """Test that supported files are correctly identified."""
    assert processor._should_process_file(Path("test.py")) is True
    assert processor._should_process_file(Path("src/component.ts")) is True

def test_should_process_file_ignored_dirs(processor):
    """Test that files in ignored directories are skipped."""
    assert processor._should_process_file(Path("node_modules/lib/index.js")) is False
    assert processor._should_process_file(Path(".git/config")) is False
    assert processor._should_process_file(Path("project/venv/lib/python3.9/site-packages/test.py")) is False

def test_should_process_file_unsupported_extension(processor):
    """Test that files with unsupported extensions are skipped."""
    assert processor._should_process_file(Path("image.jpg")) is False
    assert processor._should_process_file(Path("archive.zip")) is False
    assert processor._should_process_file(Path("document.docx")) is False # Note: python-docx is for reading, not general processing

def test_extract_files_content_from_mock_repo(processor, mock_repo: Path):
    """Integration test for file extraction using the mock repo fixture."""
    files_data = processor.extract_files_content(mock_repo)
    
    # Expected number of files to be processed:
    # - main.py
    # - README.md
    # - src/utils.js
    # - empty.py
    # Ignored: node_modules/*, data.bin, large_file.txt
    assert len(files_data) == 4

    paths = {file['path'] for file in files_data}
    assert "main.py" in paths
    assert "README.md" in paths
    assert str(Path("src/utils.js")) in paths
    assert "empty.py" in paths
    
    # Check that ignored files are not present
    assert "data.bin" not in paths
    assert str(Path("node_modules/some_lib/ignored_file.js")) not in paths
    assert "large_file.txt" not in paths

    # Check content of one file
    main_py_data = next((f for f in files_data if f['path'] == 'main.py'), None)
    assert main_py_data is not None
    assert main_py_data['content'] == "print('hello world')"
    assert main_py_data['extension'] == ".py" 
