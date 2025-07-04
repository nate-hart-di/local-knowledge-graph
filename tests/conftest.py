import pytest
from pathlib import Path
import os

@pytest.fixture(scope="session")
def test_config(tmp_path_factory):
    """Fixture to override the config to use a temporary directory for all data."""
    # Create a temporary base directory for the session
    base_dir = tmp_path_factory.mktemp("kg_test_data")
    
    # Define paths within the temp directory
    data_dir = base_dir / "data"
    repos_dir = base_dir / "repos"
    vector_db_dir = base_dir / "vector_db"
    
    # Create the directories
    data_dir.mkdir()
    repos_dir.mkdir()
    vector_db_dir.mkdir()
    
    # Set environment variables to point the Config class to these temp dirs
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["REPOS_DIR"] = str(repos_dir)
    os.environ["VECTOR_DB_DIR"] = str(vector_db_dir)
    os.environ["VECTOR_DB_TYPE"] = "chroma" # Use Chroma for simple file-based tests

    # Yield control to the tests
    yield

    # Teardown: Unset environment variables after the test session
    del os.environ["DATA_DIR"]
    del os.environ["REPOS_DIR"]
    del os.environ["VECTOR_DB_DIR"]
    del os.environ["VECTOR_DB_TYPE"]


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    """Creates a mock repository structure in a temporary directory."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Supported files
    (repo_dir / "main.py").write_text("print('hello world')")
    (repo_dir / "README.md").write_text("# Test Repo")
    
    # Nested file
    nested_dir = repo_dir / "src"
    nested_dir.mkdir()
    (nested_dir / "utils.js").write_text("console.log('utils');")

    # Ignored directory
    ignored_dir = repo_dir / "node_modules" / "some_lib"
    ignored_dir.mkdir(parents=True)
    (ignored_dir / "ignored_file.js").write_text("ignored")

    # File with unsupported extension
    (repo_dir / "data.bin").write_bytes(b"\x01\x02\x03")

    # Empty file (should be processed)
    (repo_dir / "empty.py").write_text("")

    # Large file (should be ignored)
    large_file = repo_dir / "large_file.txt"
    with open(large_file, "w") as f:
        f.write("a" * (3 * 1024 * 1024)) # 3MB

    return repo_dir 
