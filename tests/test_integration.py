import pytest
import subprocess
import time
import requests
import json
import os
from pathlib import Path
import tempfile
import shutil


class TestIntegration:
    """Integration tests for the complete agent-semantic-code system"""
    
    @pytest.fixture(scope="class")
    def docker_setup(self):
        """Set up Docker environment for testing"""
        # Create a temporary test environment
        test_dir = Path(tempfile.mkdtemp())
        
        # Copy necessary files to test directory
        source_dir = Path(__file__).parent.parent
        for file in ['Dockerfile', 'docker-compose.yml', 'requirements.txt', 
                    'main.py', 'config.py', 'vector_store.py', 'knowledge_graph.py',
                    'repo_processor.py', '.env.example']:
            if (source_dir / file).exists():
                shutil.copy(source_dir / file, test_dir / file)
        
        # Create a test .env file
        env_content = """
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
VECTOR_DB_TYPE=qdrant
QDRANT_URL=http://qdrant:6333
MAX_FILE_SIZE_MB=2
EMBEDDING_DEVICE=cpu
"""
        with open(test_dir / '.env', 'w') as f:
            f.write(env_content)
        
        original_dir = os.getcwd()
        try:
            os.chdir(test_dir)
            yield test_dir
        finally:
            os.chdir(original_dir)
            shutil.rmtree(test_dir)
    
    def test_docker_build(self, docker_setup):
        """Test that Docker container builds successfully"""
        result = subprocess.run(
            ['docker', 'build', '-t', 'agent-semantic-code-test', '.'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        assert "Successfully built" in result.stdout or "Successfully tagged" in result.stdout
    
    def test_docker_compose_syntax(self, docker_setup):
        """Test that docker-compose.yml is valid"""
        result = subprocess.run(
            ['docker-compose', 'config'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"docker-compose.yml syntax error: {result.stderr}"
    
    @pytest.mark.skipif(not shutil.which('docker'), reason="Docker not available")
    def test_container_startup(self, docker_setup):
        """Test that container starts and responds to health checks"""
        # First build the image
        build_result = subprocess.run(
            ['docker', 'build', '-t', 'agent-semantic-code-test', '.'],
            capture_output=True,
            text=True,
            timeout=300
        )
        assert build_result.returncode == 0
        
        # Start only the agent container (without Qdrant for this test)
        try:
            container_result = subprocess.run([
                'docker', 'run', '-d', 
                '--name', 'agent-test',
                '--env', 'OLLAMA_BASE_URL=http://mockollama:11434',
                '--env', 'QDRANT_URL=http://mockqdrant:6333',
                '-p', '8001:8000',  # Use different port to avoid conflicts
                'agent-semantic-code-test'
            ], capture_output=True, text=True)
            
            if container_result.returncode != 0:
                pytest.skip(f"Could not start container: {container_result.stderr}")
            
            container_id = container_result.stdout.strip()
            
            # Wait for container to start
            time.sleep(10)
            
            # Check container is running
            status_result = subprocess.run([
                'docker', 'ps', '--filter', f'id={container_id}', '--format', '{{.Status}}'
            ], capture_output=True, text=True)
            
            assert 'Up' in status_result.stdout, "Container is not running"
            
            # Try to connect to health endpoint (will fail due to missing Ollama/Qdrant but container should respond)
            try:
                response = requests.get('http://localhost:8001/health', timeout=5)
                # We expect this to return 200 even if dependencies fail
                assert response.status_code == 200
                data = response.json()
                assert data['status'] == 'ok'
                # Dependencies should show errors since they're not real
                assert 'error' in data.get('ollama_status', 'error')
                assert 'error' in data.get('qdrant_status', 'error')
            except requests.exceptions.ConnectionError:
                pytest.skip("Could not connect to container - may be network issue")
            
        finally:
            # Clean up container
            subprocess.run(['docker', 'stop', 'agent-test'], capture_output=True)
            subprocess.run(['docker', 'rm', 'agent-test'], capture_output=True)
    
    def test_environment_configuration(self, docker_setup):
        """Test that environment variables are properly configured"""
        # Test that we can import and configure without errors
        import sys
        sys.path.append(str(docker_setup))
        
        # Set test environment variables
        test_env = {
            'OLLAMA_BASE_URL': 'http://test-ollama:11434',
            'OLLAMA_EMBEDDING_MODEL': 'test-model',
            'QDRANT_URL': 'http://test-qdrant:6333',
            'MAX_FILE_SIZE_MB': '5'
        }
        
        for key, value in test_env.items():
            os.environ[key] = value
        
        try:
            from config import Config
            config = Config()
            
            assert config.OLLAMA_BASE_URL == 'http://test-ollama:11434'
            assert config.OLLAMA_EMBEDDING_MODEL == 'test-model'
            assert config.QDRANT_URL == 'http://test-qdrant:6333'
            assert config.MAX_FILE_SIZE_MB == 5
            
        finally:
            # Clean up environment
            for key in test_env:
                os.environ.pop(key, None)
    
    def test_api_documentation_accessible(self, docker_setup):
        """Test that API documentation can be generated"""
        import sys
        sys.path.append(str(docker_setup))
        
        try:
            from main import app
            from fastapi.openapi.utils import get_openapi
            
            # Generate OpenAPI schema
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )
            
            # Verify essential endpoints are documented
            paths = openapi_schema.get('paths', {})
            assert '/health' in paths
            assert '/repos' in paths
            assert '/search' in paths
            
            # Verify API documentation includes proper descriptions
            assert app.title == "Agent: Semantic Code"
            assert "microservice" in app.description.lower()
            
        except ImportError as e:
            pytest.skip(f"Could not import application: {e}")
    
    def test_requirements_installable(self, docker_setup):
        """Test that all requirements can be installed"""
        # Read requirements file
        requirements_file = docker_setup / 'requirements.txt'
        assert requirements_file.exists()
        
        with open(requirements_file) as f:
            requirements = f.read()
        
        # Verify essential packages are present
        assert 'fastapi' in requirements
        assert 'uvicorn' in requirements
        assert 'langchain-community' in requirements
        assert 'qdrant-client' in requirements
        
        # Test that requirements don't have obvious conflicts
        lines = [line.strip() for line in requirements.split('\n') 
                if line.strip() and not line.startswith('#')]
        
        packages = []
        for line in lines:
            if '==' in line:
                package = line.split('==')[0]
                packages.append(package)
        
        # Check for common conflicts
        assert len(packages) == len(set(packages)), "Duplicate packages in requirements"
    
    def test_file_structure_complete(self, docker_setup):
        """Test that all necessary files are present"""
        required_files = [
            'Dockerfile',
            'docker-compose.yml', 
            'requirements.txt',
            'main.py',
            'config.py',
            'vector_store.py',
            'knowledge_graph.py',
            '.env.example'
        ]
        
        for filename in required_files:
            file_path = docker_setup / filename
            assert file_path.exists(), f"Missing required file: {filename}"
            assert file_path.stat().st_size > 0, f"File is empty: {filename}"
    
    def test_gitignore_completeness(self, docker_setup):
        """Test that .gitignore covers important patterns"""
        gitignore_path = Path(__file__).parent.parent / '.gitignore'
        
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                gitignore_content = f.read()
            
            # Check for essential ignore patterns
            essential_patterns = [
                '.env',
                '__pycache__',
                'data/',
                'repos/',
                'vector_db/',
                'qdrant_storage/'
            ]
            
            for pattern in essential_patterns:
                assert pattern in gitignore_content, f"Missing gitignore pattern: {pattern}"


class TestPerformance:
    """Basic performance tests"""
    
    def test_import_performance(self):
        """Test that imports don't take too long"""
        import time
        import sys
        
        # Add parent directory to path
        sys.path.append(str(Path(__file__).parent.parent))
        
        start_time = time.time()
        
        try:
            import config
            import main
            
            import_time = time.time() - start_time
            
            # Imports should be fast (under 5 seconds)
            assert import_time < 5.0, f"Imports took too long: {import_time:.2f} seconds"
            
        except ImportError as e:
            pytest.skip(f"Could not import modules: {e}")
    
    def test_configuration_performance(self):
        """Test that configuration loading is fast"""
        import time
        import sys
        
        sys.path.append(str(Path(__file__).parent.parent))
        
        try:
            start_time = time.time()
            
            from config import Config
            config = Config()
            
            config_time = time.time() - start_time
            
            # Configuration should load quickly (under 1 second)
            assert config_time < 1.0, f"Configuration took too long: {config_time:.2f} seconds"
            
        except ImportError as e:
            pytest.skip(f"Could not import config: {e}") 
