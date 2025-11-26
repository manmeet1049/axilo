# axilo-ingestion-service

## Overview
This project is an AWS Lambda function designed to process data. It is built using Python and packaged in a Docker container for deployment.

## Project Structure
```
axilo-ingestion-service
├── app.py                # Main application code for the AWS Lambda function
├── requirements.txt      # Python dependencies required for the project
├── dockerfile            # Instructions to build a Docker image for the Lambda function
├── tests                 # Directory containing unit tests
│   └── test_app.py      # Unit tests for the application
├── scripts               # Directory containing deployment scripts
│   └── deploy.sh        # Shell script to automate the deployment process
└── README.md             # Documentation for the project
```

## Setup Instructions
1. Clone the repository:
   ```
   git clone <repository-url>
   cd axilo-ingestion-service
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Build the Docker image:
   ```
   docker build -t axilo-ingestion-service .
   ```

## Usage
To invoke the Lambda function locally, you can use the following command:
```
docker run -p 9000:8080 axilo-ingestion-service
```
You can then send a test event to the function using curl:
```
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
```

## Deployment
To deploy the Lambda function, run the deployment script:
```
bash scripts/deploy.sh
```

## Testing
To run the unit tests, execute:
```
pytest tests/test_app.py
```

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.