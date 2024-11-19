import boto3


def setup_bedrock_kb(credentials_secret_arn: str,
                     database_name: str, aurora_cluster_arn: str, table_name: str):
    # Create Bedrock Knowledgebase
    bedrock_client = boto3.client("bedrock-agent")
    bedrock_client.create_knowledge_base(
        name="ChocolateFactoryKB",
        description="Knowledge base for Chocolate Factory",
        schema={
            "id": "uuid",
            "embedding": "vector(1024)",
            "chunks": "text",
            "metadata": "json"
        },
        index="hnsw",
        knowledgeBaseConfiguration={
            'rdsConfiguration': {
                'credentialsSecretArn': credentials_secret_arn,
                'databaseName': database_name,
                'fieldMapping': {
                    'metadataField': 'metadata',
                    'primaryKeyField': 'uuid',
                    'textField': 'chunks',
                    'vectorField': 'embedding'
                },
                'resourceArn': aurora_cluster_arn,
                'tableName': table_name
            }
        }

    )

