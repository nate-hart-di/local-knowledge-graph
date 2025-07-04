import pytest
from pathlib import Path
import os
import shutil
import sys
sys.path.append('..')

from knowledge_graph import LocalKnowledgeGraph

# This fixture automatically applies the temporary directory settings for all tests in this file
pytestmark = pytest.mark.usefixtures("test_config")

@pytest.fixture
def kg_instance():
    """Returns a fresh instance of LocalKnowledgeGraph for each test."""
    # Ensure the directory for this test run is clean before starting
    from config import Config
    # Clean up any potential leftover data from a previous failed run
    if Config.DATA_DIR.exists():
        shutil.rmtree(Config.DATA_DIR)
        Config.DATA_DIR.mkdir()
    if Config.REPOS_DIR.exists():
        shutil.rmtree(Config.REPOS_DIR)
        Config.REPOS_DIR.mkdir()
        
    return LocalKnowledgeGraph(collection_name="test_collection")

def test_add_and_list_repository(kg_instance: LocalKnowledgeGraph, mock_repo: Path):
    """Test adding a repository and then listing it."""
    repo_name = "test_repo"
    result = kg_instance.add_repository(str(mock_repo), repo_name=repo_name, is_url=False)
    
    assert "error" not in result
    assert result["repo_name"] == repo_name
    assert result["files_processed"] == 4

    repos = kg_instance.list_repositories()
    assert len(repos) == 1
    assert repos[0]['name'] == repo_name
    assert repos[0]['files_processed'] == 4

def test_search_repository(kg_instance: LocalKnowledgeGraph, mock_repo: Path):
    """Test searching for content within an added repository."""
    kg_instance.add_repository(str(mock_repo), repo_name="search_repo", is_url=False)
    
    # Search for content that exists
    results = kg_instance.search("hello world")
    assert len(results) > 0
    assert results[0]['path'] == "main.py"
    assert "hello world" in results[0]['content']

    # Search for content in another file
    results_js = kg_instance.search("utils")
    assert len(results_js) > 0
    assert results_js[0]['path'] == str(Path("src/utils.js"))

    # Search for content that doesn't exist
    results_none = kg_instance.search("non_existent_term_xyz")
    assert len(results_none) == 0

def test_remove_repository(kg_instance: LocalKnowledgeGraph, mock_repo: Path):
    """Test that removing a repository cleans up all associated data."""
    repo_name = "repo_to_remove"
    from config import Config

    # Add the repo and verify it exists
    kg_instance.add_repository(str(mock_repo), repo_name=repo_name, is_url=False)
    repos = kg_instance.list_repositories()
    assert len(repos) == 1
    
    # The cloned repo should exist in the temp REPOS_DIR
    temp_repo_path = Config.REPOS_DIR / repo_name
    assert temp_repo_path.exists()
    
    # Remove the repo
    was_removed = kg_instance.remove_repository(repo_name)
    assert was_removed is True

    # Verify everything is gone
    repos_after_removal = kg_instance.list_repositories()
    assert len(repos_after_removal) == 0

    # Search should yield no results
    results = kg_instance.search("hello world")
    assert len(results) == 0

    # The cloned directory should be gone
    assert not temp_repo_path.exists() 
