import hashlib
import boto3
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from config import settings


class DynamoDBClient:
    """DynamoDB client with automatic table creation and management"""
    
    def __init__(self):
        """Initialize DynamoDB client and ensure table exists"""
        self.table_name = settings.dynamodb_table_name
        self.region = settings.dynamodb_region
        
        # Build boto3 resource kwargs
        resource_kwargs = {
            'region_name': self.region
        }
        
        # Add credentials if provided (for local/dev environments)
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            resource_kwargs['aws_access_key_id'] = settings.aws_access_key_id
            resource_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key
        
        # Add endpoint URL if provided (for LocalStack/DynamoDB Local)
        if settings.dynamodb_endpoint_url:
            resource_kwargs['endpoint_url'] = settings.dynamodb_endpoint_url
            print(f"Using DynamoDB endpoint: {settings.dynamodb_endpoint_url}")
        
        # Initialize DynamoDB resource
        self.dynamodb = boto3.resource('dynamodb', **resource_kwargs)
        self.client = self.dynamodb.meta.client
        
        # Ensure table exists
        self._ensure_table_exists()
        self.table = self.dynamodb.Table(self.table_name)
    
    def _ensure_table_exists(self):
        """Check if table exists, create if not"""
        try:
            # Try to describe the table
            self.client.describe_table(TableName=self.table_name)
            print(f"Table '{self.table_name}' already exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Table '{self.table_name}' not found. Creating...")
                self._create_table()
            else:
                raise
    
    def _create_table(self):
        """Create DynamoDB table with single-table design"""
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'PK',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'SK',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'SK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'GSI1PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'GSI1SK',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'GSI1',
                        'KeySchema': [
                            {
                                'AttributeName': 'GSI1PK',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'GSI1SK',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                BillingMode='PAY_PER_REQUEST',  # On-demand pricing
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'Axilo'
                    },
                    {
                        'Key': 'Purpose',
                        'Value': 'Code Metadata Storage'
                    }
                ]
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            print(f"Table '{self.table_name}' created successfully")
            
        except ClientError as e:
            print(f"Error creating table: {e}")
            raise
    
    @staticmethod
    def get_repo_id(repo_url: str) -> str:
        """Generate consistent repo ID from URL"""
        url = repo_url.lower().strip().rstrip('/')
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def put_repository_metadata(self, repo_url: str, repo_name: str, 
                               structure: Dict, stats: Dict) -> bool:
        """
        Store repository metadata
        
        Args:
            repo_url: Full repository URL
            repo_name: Repository name
            structure: Repository structure JSON
            stats: Statistics about the repository
        """
        try:
            repo_id = self.get_repo_id(repo_url)
            
            item = {
                'PK': f'REPO#{repo_id}',
                'SK': 'METADATA',
                'Type': 'repository',
                'repo_url': repo_url,
                'repo_name': repo_name,
                'total_files': stats.get('total_files', 0),
                'python_files_parsed': stats.get('python_files_parsed', 0),
            }
            
            # Add structure if not empty
            if structure:
                item['structure'] = structure
            
            # Add stats if not empty
            if stats:
                item['stats'] = stats
            
            # Remove any empty strings, None values, or empty dicts/lists
            item = self._clean_item(item)
            
            self.table.put_item(Item=item)
            print(f"Stored repository metadata for {repo_name}")
            return True
            
        except ClientError as e:
            import traceback
            traceback.print_exc()
            print(f"Error storing repository metadata: {e}")
            return False
    
    def _clean_item(self, item: Dict) -> Dict:
        """
        Remove empty values from item to prevent DynamoDB validation errors
        
        Args:
            item: Dictionary to clean
            
        Returns:
            Cleaned dictionary
        """
        cleaned = {}
        for key, value in item.items():
            # Skip if key is empty or whitespace
            if not key or not str(key).strip():
                print(f"Warning: Skipping empty key")
                continue
                
            # Skip empty strings
            if value == '':
                continue
            # Skip None values
            if value is None:
                continue
            # Skip empty collections
            if isinstance(value, (dict, list)) and not value:
                continue
            # Recursively clean nested dicts
            if isinstance(value, dict):
                cleaned_value = self._clean_dict(value)
                if cleaned_value:  # Only add if not empty after cleaning
                    cleaned[key] = cleaned_value
            # Clean lists of dicts
            elif isinstance(value, list):
                cleaned_list = self._clean_list(value)
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _clean_dict(self, d: Dict) -> Dict:
        """Recursively clean a dictionary"""
        cleaned = {}
        for key, value in d.items():
            # Skip empty keys
            if not key or not str(key).strip():
                continue
            # Skip empty values
            if value == '' or value is None:
                continue
            if isinstance(value, (dict, list)) and not value:
                continue
            # Recurse into nested structures
            if isinstance(value, dict):
                cleaned_value = self._clean_dict(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            elif isinstance(value, list):
                cleaned_value = self._clean_list(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            else:
                cleaned[key] = value
        return cleaned
    
    def _clean_list(self, lst: list) -> list:
        """Clean a list, handling nested dicts"""
        cleaned = []
        for item in lst:
            if item == '' or item is None:
                continue
            if isinstance(item, dict):
                cleaned_item = self._clean_dict(item)
                if cleaned_item:
                    cleaned.append(cleaned_item)
            elif isinstance(item, list):
                cleaned_item = self._clean_list(item)
                if cleaned_item:
                    cleaned.append(cleaned_item)
            else:
                # Skip empty strings/None in lists
                if item != '' and item is not None:
                    cleaned.append(item)
        return cleaned
    
    def put_file_metadata(self, repo_url: str, file_path: str, 
                         md_content: str, metadata: Dict) -> bool:
        """
        Store file metadata
        
        Args:
            repo_url: Repository URL
            file_path: Relative file path
            md_content: Markdown content
            metadata: Parsed metadata dictionary
        """
        try:
            repo_id = self.get_repo_id(repo_url)
            
            # Extract summary info from metadata
            functions = [f.get('name') for f in metadata.get('functions', []) if f.get('name')]
            classes = [c.get('name') for c in metadata.get('classes', []) if c.get('name')]
            
            # Count calls
            total_calls = sum(len(f.get('calls', [])) for f in metadata.get('functions', []))
            for cls in metadata.get('classes', []):
                for method in cls.get('methods', []):
                    total_calls += len(method.get('calls', []))
            
            item = {
                'PK': f'REPO#{repo_id}',
                'SK': f'FILE#{file_path}',
                'Type': 'file',
                'file_path': file_path,
                'md_content': md_content,
                'total_calls': total_calls,
                # GSI for querying by file type
                'GSI1PK': f'TYPE#{file_path.split(".")[-1]}',
                'GSI1SK': f'REPO#{repo_id}#FILE#{file_path}'
            }
            
            # Add optional fields only if not empty
            if functions:
                item['functions'] = functions
            if classes:
                item['classes'] = classes
            if metadata.get('imports'):
                item['imports'] = metadata['imports']
            
            # Clean the item
            item = self._clean_item(item)
            
            self.table.put_item(Item=item)
            return True
            
        except ClientError as e:
            print(f"Error storing file metadata for {file_path}: {e}")
            return False
    
    def get_repository_metadata(self, repo_url: str) -> Optional[Dict]:
        """Get repository metadata by URL"""
        try:
            repo_id = self.get_repo_id(repo_url)
            
            response = self.table.get_item(
                Key={
                    'PK': f'REPO#{repo_id}',
                    'SK': 'METADATA'
                }
            )
            
            return response.get('Item')
            
        except ClientError as e:
            print(f"Error getting repository metadata: {e}")
            return None
    
    def get_all_files_for_repo(self, repo_url: str) -> List[Dict]:
        """Get all file metadata for a repository"""
        try:
            repo_id = self.get_repo_id(repo_url)
            
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'REPO#{repo_id}',
                    ':sk': 'FILE#'
                }
            )
            
            return response.get('Items', [])
            
        except ClientError as e:
            print(f"Error getting files for repository: {e}")
            return []
    
    def get_file_metadata(self, repo_url: str, file_path: str) -> Optional[Dict]:
        """Get specific file metadata"""
        try:
            repo_id = self.get_repo_id(repo_url)
            
            response = self.table.get_item(
                Key={
                    'PK': f'REPO#{repo_id}',
                    'SK': f'FILE#{file_path}'
                }
            )
            
            return response.get('Item')
            
        except ClientError as e:
            print(f"Error getting file metadata: {e}")
            return None
    
    def delete_repository(self, repo_url: str) -> bool:
        """Delete all data for a repository"""
        try:
            repo_id = self.get_repo_id(repo_url)
            
            # Query all items for this repo
            response = self.table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'REPO#{repo_id}'
                }
            )
            
            # Delete all items
            with self.table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        }
                    )
            
            print(f"Deleted all data for repository {repo_url}")
            return True
            
        except ClientError as e:
            print(f"Error deleting repository: {e}")
            return False
    
    def batch_put_files(self, repo_url: str, files_data: List[Dict]) -> bool:
        """
        Batch insert multiple file metadata items
        
        Args:
            repo_url: Repository URL
            files_data: List of dicts with 'file_path', 'md_content', 'metadata'
        """
        try:
            repo_id = self.get_repo_id(repo_url)
            
            with self.table.batch_writer() as batch:
                for file_data in files_data:
                    file_path = file_data['file_path']
                    md_content = file_data['md_content']
                    metadata = file_data['metadata']
                    
                    # Extract summary info
                    functions = [f.get('name') for f in metadata.get('functions', []) if f.get('name')]
                    classes = [c.get('name') for c in metadata.get('classes', []) if c.get('name')]
                    
                    item = {
                        'PK': f'REPO#{repo_id}',
                        'SK': f'FILE#{file_path}',
                        'Type': 'file',
                        'file_path': file_path,
                        'md_content': md_content,
                        'GSI1PK': f'TYPE#{file_path.split(".")[-1]}',
                        'GSI1SK': f'REPO#{repo_id}#FILE#{file_path}'
                    }
                    
                    # Add optional fields only if not empty
                    if functions:
                        item['functions'] = functions
                    if classes:
                        item['classes'] = classes
                    if metadata.get('imports'):
                        item['imports'] = metadata['imports']
                    
                    # Clean the item
                    item = self._clean_item(item)
                    
                    batch.put_item(Item=item)
            
            print(f"Batch inserted {len(files_data)} files")
            return True
            
        except ClientError as e:
            print(f"Error batch inserting files: {e}")
            return False
