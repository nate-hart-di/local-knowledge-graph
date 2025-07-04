import json
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import dataclasses

from repo_processor import LocalRepoProcessor
from vector_store import LocalVectorStore
from config import Config

class LocalKnowledgeGraph:
    def __init__(self, collection_name: str = "repo_knowledge"):
        self.config = Config()
        self.repo_processor = LocalRepoProcessor()
        self.vector_store = LocalVectorStore(collection_name)
        self.processed_repos_path = self.config.DATA_DIR / "processed_repos.json"
        self.processed_repos = self._load_processed_repos()
    
    def _load_processed_repos(self) -> Dict[str, Dict]:
        """Load metadata of previously processed repositories"""
        if self.processed_repos_path.exists():
            with open(self.processed_repos_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print("Could not read processed_repos.json, starting fresh.")
                    return {}
        return {}
    
    def _save_processed_repos(self):
        """Save metadata of processed repositories"""
        with open(self.processed_repos_path, 'w', encoding='utf-8') as f:
            json.dump(self.processed_repos, f, indent=2, ensure_ascii=False)
    
    def add_repository(self, repo_source: str, repo_name: Optional[str] = None, is_url: bool = True) -> Dict[str, Any]:
        """Add a new repository to the knowledge graph."""
        print(f"🔄 Adding repository to knowledge graph: {repo_source}")
        
        repo_info = self.repo_processor.process_repository(repo_source, is_url)
        if not repo_info or not repo_info.get('files_processed'):
            print("No files were processed. Aborting.")
            return {"error": "No files were processed from the repository."}

        effective_repo_name = repo_name or repo_info['metadata'].name
        
        with open(repo_info['data_file'], 'r', encoding='utf-8') as f:
            repo_data = json.load(f)
        
        documents = [
            {**file_data, 'repo_name': effective_repo_name}
            for file_data in repo_data['files']
        ]
        
        print(f"📊 Adding {len(documents)} documents to vector store...")
        docs_added = self.vector_store.add_documents(documents)
        
        self.processed_repos[effective_repo_name] = {
            'source': repo_source,
            'is_url': is_url,
            'processed_at': datetime.now().isoformat(),
            'files_processed': len(documents),
            'data_file': repo_info['data_file'],
            'repo_path': repo_info['repo_path']
        }
        self._save_processed_repos()
        
        summary = {
            'repo_name': effective_repo_name,
            'files_processed': len(documents),
            'documents_added': docs_added,
            'metadata': dataclasses.asdict(repo_info['metadata']),
        }
        
        print(f"✅ Repository '{effective_repo_name}' added successfully!")
        return summary
    
    def search(self, query: str, limit: int = 10, repo_filter: Optional[str] = None) -> List[Dict]:
        """Search across all repositories."""
        print(f"🔍 Searching for: '{query}'")
        if repo_filter:
            print(f"   Filtering by repository: {repo_filter}")
        
        results = self.vector_store.search(query, limit, repo_filter)
        print(f"   Found {len(results)} results.")
        return results
    
    def get_repository_info(self, repo_name: str) -> Optional[Dict]:
        """Get information about a specific repository."""
        return self.processed_repos.get(repo_name)
    
    def list_repositories(self) -> List[Dict]:
        """List all processed repositories with their metadata."""
        return [
            {'name': name, **info}
            for name, info in self.processed_repos.items()
        ]
    
    def update_repository(self, repo_name: str) -> Dict[str, Any]:
        """Update an existing repository by re-processing it."""
        if repo_name not in self.processed_repos:
            raise ValueError(f"Repository '{repo_name}' not found.")
        
        repo_info = self.processed_repos[repo_name]
        print(f"🔄 Updating repository: {repo_name}")
        
        self.vector_store.delete_repo(repo_name)
        
        return self.add_repository(
            repo_info['source'],
            repo_name,
            repo_info['is_url']
        )
    
    def remove_repository(self, repo_name: str) -> bool:
        """Remove a repository and all its associated documents."""
        if repo_name not in self.processed_repos:
            return False
        
        print(f"🗑️ Removing repository: {repo_name}")
        self.vector_store.delete_repo(repo_name)
        
        repo_info = self.processed_repos[repo_name]

        # Clean up cloned repo directory
        repo_path = Path(repo_info.get('repo_path', ''))
        if repo_path.exists() and self.config.REPOS_DIR in repo_path.parents:
            shutil.rmtree(repo_path)
            print(f"   Removed cloned directory: {repo_path}")
        
        # Clean up data file
        data_file = Path(repo_info.get('data_file', ''))
        if data_file.exists():
            data_file.unlink()
            print(f"   Removed data file: {data_file}")

        del self.processed_repos[repo_name]
        self._save_processed_repos()
        
        print(f"✅ Repository '{repo_name}' removed successfully!")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge graph."""
        vector_stats = self.vector_store.get_stats()
        
        languages = {}
        total_files = 0
        for repo_info in self.processed_repos.values():
            total_files += repo_info['files_processed']
            try:
                with open(repo_info['data_file'], 'r', encoding='utf-8') as f:
                    repo_data = json.load(f)
                
                for lang, count in repo_data['metadata']['languages'].items():
                    languages[lang] = languages.get(lang, 0) + count
            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                continue
        
        return {
            'total_repositories': len(self.processed_repos),
            'total_files': total_files,
            'languages': languages,
            'vector_db': vector_stats,
            'repositories': self.list_repositories()
        }
    
    def export_knowledge_graph(self, output_file: str) -> str:
        """Export key metadata of the knowledge graph to a file."""
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'stats': self.get_stats(),
        }
        
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"📤 Knowledge graph summary exported to: {output_path}")
        return str(output_path)
    
    def semantic_search_with_context(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Perform semantic search and group results by repository."""
        results = self.search(query, limit * 2) # Fetch more to get diversity
        
        repo_results = {}
        for res in results:
            repo_name = res['repo_name']
            if repo_name not in repo_results:
                repo_results[repo_name] = {'matching_files': [], 'total_score': 0}
            repo_results[repo_name]['matching_files'].append(res)
            repo_results[repo_name]['total_score'] += res['score']

        # Calculate relevance and sort
        final_results = {}
        for repo, data in repo_results.items():
            final_results[repo] = {
                'relevance_score': data['total_score'] / len(data['matching_files']),
                'matching_files': sorted(data['matching_files'], key=lambda x: x['score'], reverse=True)
            }
        
        sorted_repos = sorted(final_results.items(), key=lambda item: item[1]['relevance_score'], reverse=True)

        return {
            'query': query,
            'total_results': len(results),
            'repositories_found': len(repo_results),
            'results_by_repository': dict(sorted_repos[:limit])
        }

 
