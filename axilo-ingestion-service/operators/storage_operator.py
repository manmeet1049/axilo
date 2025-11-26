import os
import json
from typing import Dict, List, Tuple
from clients import DynamoDBClient


class StorageOperator:
    """Handles storing metadata to DynamoDB"""
    
    def __init__(self):
        """Initialize DynamoDB client"""
        self.db_client = DynamoDBClient()
    
    def store_repository_data(self, repo_url: str, repo_name: str, 
                              structure: Dict, stats: Dict,
                              metadata_path: str) -> Tuple[bool, Dict]:
        """
        Store repository structure and all file metadata to DynamoDB
        
        Args:
            repo_url: Repository URL
            repo_name: Repository name
            structure: Repository structure JSON
            stats: Repository statistics
            metadata_path: Path to metadata directory
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        try:
            # Store repository metadata
            print(f"Storing repository metadata for {repo_name}...")
            success = self.db_client.put_repository_metadata(
                repo_url=repo_url,
                repo_name=repo_name,
                structure=structure,
                stats=stats
            )
            
            if not success:
                return False, {'error': 'Failed to store repository metadata'}
            
            # Collect all metadata files
            files_data = self._collect_metadata_files(metadata_path, repo_name)
            
            if not files_data:
                return True, {
                    'message': 'Repository metadata stored, no files to store',
                    'repo_name': repo_name,
                    'files_stored': 0
                }
            
            # Batch store file metadata
            print(f"Storing {len(files_data)} file metadata items...")
            success = self.db_client.batch_put_files(repo_url, files_data)
            
            if success:
                return True, {
                    'message': 'Repository data stored successfully',
                    'repo_name': repo_name,
                    'files_stored': len(files_data),
                    'repo_url': repo_url
                }
            else:
                return False, {'error': 'Failed to store file metadata'}
            
        except Exception as e:
            print(f"Error storing repository data: {e}")
            import traceback
            traceback.print_exc()
            return False, {'error': str(e)}
    
    def _collect_metadata_files(self, metadata_path: str, repo_name: str) -> List[Dict]:
        """
        Collect all metadata files from the metadata directory
        
        Args:
            metadata_path: Path to metadata directory
            repo_name: Repository name
            
        Returns:
            List of file data dictionaries
        """
        files_data = []
        
        if not os.path.exists(metadata_path):
            print(f"Metadata path does not exist: {metadata_path}")
            return files_data
        
        # Walk through metadata directory
        for root, dirs, files in os.walk(metadata_path):
            for file in files:
                if file.endswith('.md') or file.endswith('.json'):
                    file_full_path = os.path.join(root, file)
                    
                    # Calculate relative path from metadata base
                    rel_path = os.path.relpath(file_full_path, metadata_path)
                    
                    # Read file content
                    try:
                        with open(file_full_path, 'r') as f:
                            content = f.read()
                        
                        # Parse metadata if JSON
                        if file.endswith('.json'):
                            metadata = json.loads(content)
                            md_content = content  # Store JSON as-is
                        else:
                            # For markdown, create a simple metadata structure
                            metadata = self._parse_markdown_metadata(content, rel_path)
                            md_content = content
                        
                        # Convert .md/.json extension back to .py for file_path
                        original_file_path = rel_path.rsplit('.', 1)[0] + '.py'
                        
                        files_data.append({
                            'file_path': original_file_path,
                            'md_content': md_content,
                            'metadata': metadata
                        })
                        
                    except Exception as e:
                        print(f"Error reading file {file_full_path}: {e}")
                        continue
        
        print(f"Collected {len(files_data)} metadata files")
        return files_data
    
    def _parse_markdown_metadata(self, md_content: str, file_path: str) -> Dict:
        """
        Extract basic metadata from markdown content
        
        Args:
            md_content: Markdown content
            file_path: File path
            
        Returns:
            Metadata dictionary
        """
        # Simple parsing - extract sections
        metadata = {
            'file_path': file_path,
            'imports': {},
            'functions': [],
            'classes': []
        }
        
        # Basic extraction from markdown
        lines = md_content.split('\n')
        current_section = None
        
        for line in lines:
            if line.startswith('## Imports'):
                current_section = 'imports'
            elif line.startswith('## Functions'):
                current_section = 'functions'
            elif line.startswith('## Classes'):
                current_section = 'classes'
            elif line.startswith('###') and current_section == 'functions':
                # Extract function name from markdown
                func_name = line.replace('###', '').strip().strip('`')
                if '(' in func_name:
                    func_name = func_name.split('(')[0]
                metadata['functions'].append({'name': func_name})
            elif line.startswith('###') and current_section == 'classes':
                # Extract class name
                class_name = line.replace('###', '').strip().strip('`')
                if '(' in class_name:
                    class_name = class_name.split('(')[0]
                metadata['classes'].append({'name': class_name})
        
        return metadata
    
    def retrieve_repository_data(self, repo_url: str) -> Tuple[bool, Dict]:
        """
        Retrieve repository data from DynamoDB
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            # Get repository metadata
            repo_metadata = self.db_client.get_repository_metadata(repo_url)
            
            if not repo_metadata:
                return False, {'error': 'Repository not found'}
            
            # Get all files
            files = self.db_client.get_all_files_for_repo(repo_url)
            
            return True, {
                'repository': repo_metadata,
                'files': files,
                'total_files': len(files)
            }
            
        except Exception as e:
            print(f"Error retrieving repository data: {e}")
            return False, {'error': str(e)}
