#!/usr/bin/env python3
"""
Command Line Interface for the Local Knowledge Graph.
"""
import argparse
import sys
from typing import Optional

from knowledge_graph import LocalKnowledgeGraph

class KnowledgeGraphCLI:
    def __init__(self):
        try:
            self.kg = LocalKnowledgeGraph()
        except Exception as e:
            print(f"❌ Failed to initialize Knowledge Graph: {e}")
            print("   Please ensure your environment is set up correctly (e.g., .env file, Docker running).")
            sys.exit(1)

    def add_repository(self, source: str, name: Optional[str] = None, is_local: bool = False):
        """Add a repository from a URL or local path."""
        print("-" * 80)
        try:
            result = self.kg.add_repository(source, name, is_url=not is_local)
            if result and not result.get("error"):
                print(f"✅ Successfully added repository: {result['repo_name']}")
                print(f"   - Files processed: {result['files_processed']}")
                print(f"   - Documents added to vector store: {result['documents_added']}")
            else:
                print(f"❌ Failed to add repository. Reason: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ An unexpected error occurred while adding repository: {e}")
        print("-" * 80)

    def search(self, query: str, limit: int, repo_filter: Optional[str]):
        """Search the knowledge graph."""
        print("-" * 80)
        results = self.kg.search(query, limit, repo_filter)
        if not results:
            print("No results found.")
            return
        
        print(f"Found {len(results)} results for '{query}':")
        for i, res in enumerate(results, 1):
            print(f"\n{i}. Path: {res['path']} (Score: {res['score']:.3f})")
            print(f"   Repo: {res['repo_name']}")
            preview = res['content'].strip().replace('\n', ' ')
            print(f"   Preview: {preview[:150]}...")
        print("-" * 80)
    
    def list_repositories(self):
        """List all repositories."""
        print("-" * 80)
        repos = self.kg.list_repositories()
        if not repos:
            print("No repositories found.")
            return
        
        print(f"Found {len(repos)} repositories:")
        for repo in sorted(repos, key=lambda r: r['name']):
            print(f"\n- {repo['name']}")
            print(f"  Source: {repo['source']}")
            print(f"  Files: {repo['files_processed']}")
            print(f"  Added: {repo['processed_at']}")
        print("-" * 80)

    def get_stats(self):
        """Display statistics about the knowledge graph."""
        print("-" * 80)
        stats = self.kg.get_stats()
        print("📊 Knowledge Graph Statistics")
        print(f"  - Total Repositories: {stats['total_repositories']}")
        print(f"  - Total Files: {stats['total_files']}")
        
        db_stats = stats['vector_db']
        if not db_stats.get('error'):
            print(f"  - Vector DB: {db_stats.get('db_type', 'N/A')}")
            print(f"    - Documents: {db_stats.get('total_documents', 'N/A')}")
            print(f"    - Dimensions: {db_stats.get('vector_size', 'N/A')}")
        else:
            print(f"  - Vector DB: Error ({db_stats['error']})")

        if stats['languages']:
            print("\n💻 Top Languages (by file count):")
            sorted_langs = sorted(stats['languages'].items(), key=lambda x: x[1], reverse=True)
            for lang, count in sorted_langs[:10]:
                print(f"  - {lang}: {count} files")
        print("-" * 80)

    def update_repository(self, repo_name: str):
        """Update a specific repository."""
        print("-" * 80)
        try:
            result = self.kg.update_repository(repo_name)
            print(f"✅ Successfully updated repository: {result['repo_name']}")
        except Exception as e:
            print(f"❌ Error updating repository: {e}")
        print("-" * 80)

    def remove_repository(self, repo_name: str):
        """Remove a repository."""
        print("-" * 80)
        if self.kg.remove_repository(repo_name):
            print(f"✅ Successfully removed repository: {repo_name}")
        else:
            print(f"❌ Repository not found: {repo_name}")
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(
        description="Local Knowledge Graph CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # Add repo
    add_parser = subparsers.add_parser('add', help='Add a new repository from a GitHub URL.')
    add_parser.add_argument('url', help='GitHub repository URL (e.g., https://github.com/user/repo)')
    add_parser.add_argument('--name', help='Optional custom name for the repository.')

    # Add local
    local_parser = subparsers.add_parser('add-local', help='Add a new repository from a local directory.')
    local_parser.add_argument('path', help='Path to the local directory.')
    local_parser.add_argument('--name', required=True, help='A name for this local repository.')

    # Search
    search_parser = subparsers.add_parser('search', help='Search the knowledge graph.')
    search_parser.add_argument('query', help='The search query.')
    search_parser.add_argument('--limit', type=int, default=10, help='Number of results to return.')
    search_parser.add_argument('--repo', help='Filter search by a specific repository name.')

    # List
    subparsers.add_parser('list', help='List all repositories in the knowledge graph.')

    # Stats
    subparsers.add_parser('stats', help='Show statistics about the knowledge graph.')

    # Update
    update_parser = subparsers.add_parser('update', help='Update an existing repository.')
    update_parser.add_argument('name', help='The name of the repository to update.')
    
    # Remove
    remove_parser = subparsers.add_parser('remove', help='Remove a repository.')
    remove_parser.add_argument('name', help='The name of the repository to remove.')

    args = parser.parse_args()
    cli = KnowledgeGraphCLI()

    try:
        if args.command == 'add':
            cli.add_repository(args.url, args.name, is_local=False)
        elif args.command == 'add-local':
            cli.add_repository(args.path, args.name, is_local=True)
        elif args.command == 'search':
            cli.search(args.query, args.limit, args.repo)
        elif args.command == 'list':
            cli.list_repositories()
        elif args.command == 'stats':
            cli.get_stats()
        elif args.command == 'update':
            cli.update_repository(args.name)
        elif args.command == 'remove':
            cli.remove_repository(args.name)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
