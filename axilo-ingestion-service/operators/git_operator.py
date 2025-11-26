import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Tuple

class GitOperator:
    """Handles git repository operations"""
    
    def __init__(self, clone_base_dir: str = '/tmp'):
        self.clone_base_dir = clone_base_dir
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        # Remove .git suffix if present
        repo_name = repo_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return repo_name
    
    def clone_repository(self, repo_url: str) -> Tuple[bool, Dict]:
        """
        Clone a git repository
        
        Args:
            repo_url: URL of the git repository
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        try:
            repo_name = self._extract_repo_name(repo_url)
            clone_dir = os.path.join(self.clone_base_dir, repo_name)
            
            # Clean up existing directory if it exists
            if os.path.exists(clone_dir):
                shutil.rmtree(clone_dir)
            
            # Clone the repository
            print(f"Cloning repository: {repo_url}")
            result = subprocess.run(
                ['git', 'clone', repo_url, clone_dir],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                return False, {
                    'error': 'Failed to clone repository',
                    'details': result.stderr
                }
            
            # Get repository info
            repo_files = list(Path(clone_dir).rglob('*'))
            file_count = len([f for f in repo_files if f.is_file()])
            
            print(f"Successfully cloned repository with {file_count} files")
            
            return True, {
                'message': 'Repository cloned successfully',
                'repo_url': repo_url,
                'repo_name': repo_name,
                'file_count': file_count,
                'clone_path': clone_dir
            }
            
        except subprocess.TimeoutExpired:
            return False, {'error': 'Repository clone timeout'}
        except Exception as e:
            return False, {'error': str(e)}
    
    def cleanup(self, clone_dir: str = None):
        """Clean up cloned repository"""
        if clone_dir is None:
            clone_dir = os.path.join(self.clone_base_dir, 'repo_clone')
        
        if os.path.exists(clone_dir):
            shutil.rmtree(clone_dir)
            print(f"Cleaned up directory: {clone_dir}")