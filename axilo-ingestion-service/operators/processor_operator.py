import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
from .parser_operator import ParserOperator

class ProcessorOperator:
    """Handles processing and creating replica of repository structure"""
    
    def __init__(self):
        self.structure = {}
        self.parser_operator = ParserOperator()
    
    def process_repository(self, repo_path: str) -> Tuple[bool, Dict]:
        """
        Process repository and create structure replica
        
        Args:
            repo_path: Path to the cloned repository
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        try:
            if not os.path.exists(repo_path):
                return False, {'error': f'Repository path does not exist: {repo_path}'}
            
            repo_name = os.path.basename(repo_path)
            
            # Create structure and parse files
            structure = self._create_structure(repo_path, repo_path, repo_name)
            
            # Get statistics
            stats = self._calculate_stats(structure)
            
            # Add parsing stats
            metadata_dir = os.path.join(self.parser_operator.metadata_base_dir, repo_name)
            stats['metadata_path'] = metadata_dir
            stats['metadata_exists'] = os.path.exists(metadata_dir)
            
            print(f"Processed repository: {repo_name}")
            print(f"Total files: {stats['total_files']}, Total directories: {stats['total_dirs']}")
            print(f"Python files parsed: {stats.get('python_files_parsed', 0)}")
            
            return True, {
                'message': 'Repository processed successfully',
                'repo_name': repo_name,
                'structure': structure,
                'stats': stats
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def _create_structure(self, path: str, repo_path: str, repo_name: str, parent_path: str = '') -> Dict:
        """
        Recursively create structure of the repository and parse Python files
        
        Args:
            path: Current path to process
            repo_path: Root path of repository
            repo_name: Name of the repository
            parent_path: Parent path for relative path calculation
            
        Returns:
            Dictionary representing the structure
        """
        structure = {
            'name': os.path.basename(path),
            'type': 'directory' if os.path.isdir(path) else 'file',
            'path': os.path.relpath(path, parent_path) if parent_path else path,
            'size': 0,
            'children': []
        }
        
        if os.path.isfile(path):
            structure['size'] = os.path.getsize(path)
            structure['extension'] = os.path.splitext(path)[1]
            
            # Parse Python files
            if structure['extension'] == '.py':
                parse_success = self.parser_operator.create_metadata_file(path, repo_path, repo_name)
                structure['parsed'] = parse_success
            
            return structure
        
        # Process directory
        try:
            items = sorted(os.listdir(path))
            
            for item in items:
                # Skip .git directory
                if item == '.git':
                    continue
                
                item_path = os.path.join(path, item)
                child_structure = self._create_structure(
                    item_path,
                    repo_path,
                    repo_name,
                    parent_path if parent_path else path
                )
                structure['children'].append(child_structure)
                
        except PermissionError:
            structure['error'] = 'Permission denied'
        
        return structure
    
    def _calculate_stats(self, structure: Dict) -> Dict:
        """Calculate statistics from structure"""
        stats = {
            'total_files': 0,
            'total_dirs': 0,
            'total_size': 0,
            'file_types': {},
            'python_files_parsed': 0
        }
        
        def traverse(node):
            if node['type'] == 'file':
                stats['total_files'] += 1
                stats['total_size'] += node.get('size', 0)
                
                ext = node.get('extension', 'no_extension')
                if ext not in stats['file_types']:
                    stats['file_types'][ext] = 0
                stats['file_types'][ext] += 1
                
                # Count parsed Python files
                if node.get('parsed', False):
                    stats['python_files_parsed'] += 1
            else:
                stats['total_dirs'] += 1
                for child in node.get('children', []):
                    traverse(child)
        
        traverse(structure)
        return stats
    
    def save_structure_to_file(self, structure: Dict, output_path: str) -> bool:
        """
        Save structure to JSON file
        
        Args:
            structure: Repository structure
            output_path: Path to save the JSON file
            
        Returns:
            Success status
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(structure, f, indent=2)
            print(f"Structure saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error saving structure: {e}")
            return False