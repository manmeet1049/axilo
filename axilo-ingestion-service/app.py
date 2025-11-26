import json

from operators import GitOperator, ProcessorOperator, StorageOperator



def lambda_handler(event, context=None):
    """
    Lambda handler to clone a git repository, process it, and store to DynamoDB
    
    Expected event structure:
    {
        "repo_url": "https://github.com/username/repo.git"
    }
    """
    try:
        repo_url = event.get('repo_url')
        
        if not repo_url:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'repo_url is required'})
            }
        
        git_operator = GitOperator()
        processor_operator = ProcessorOperator()
        storage_operator = StorageOperator()
        
        print(f"Cloning repository: {repo_url}")
        success, clone_result = git_operator.clone_repository(repo_url)
        
        if not success:
            return {
                'statusCode': 500,
                'body': json.dumps(clone_result)
            }
        
        clone_path = clone_result['clone_path']
        print(f"Processing repository at: {clone_path}")
        success, process_result = processor_operator.process_repository(clone_path)
        
        if not success:
            return {
                'statusCode': 500,
                'body': json.dumps(process_result)
            }
        
        print(f"Storing repository data to DynamoDB...")
        success, storage_result = storage_operator.store_repository_data(
            repo_url=repo_url,
            repo_name=process_result['repo_name'],
            structure=process_result['structure'],
            stats=process_result['stats'],
            metadata_path=process_result['stats'].get('metadata_path', '')
        )
        
        git_operator.cleanup(clone_path)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Repository ingested successfully',
                    'clone_info': clone_result,
                    'process_info': process_result,
                    'storage_info': storage_result
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Failed to store repository data',
                    'error': storage_result
                })
            }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For local testing
if __name__ == '__main__':
    result = lambda_handler({'repo_url': 'https://github.com/manmeet1049/envyro'})
    print(json.dumps(result, indent=2))