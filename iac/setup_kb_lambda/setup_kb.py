import cfnresponse
import string
import random
import psycopg2
import os
import boto3
from botocore.exceptions import ClientError
import json

def id_generator(size, chars=string.ascii_lowercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))

def get_secret(secret_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    return get_secret_value_response['SecretString']

def setup_rds(database_name: str, host: str, user: str, password: str, port: str):
    sql_statements_to_setup_bedrock_kb = [
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "SELECT extversion FROM pg_extension WHERE extname='vector';",
        "CREATE SCHEMA bedrock_integration;",
        f"CREATE ROLE bedrock_user WITH PASSWORD '{password}' LOGIN;",
        "GRANT ALL ON SCHEMA bedrock_integration to bedrock_user;",
        "CREATE TABLE bedrock_integration.bedrock_kb (id uuid PRIMARY KEY, embedding vector(1024), chunks text, metadata json);",
        "CREATE INDEX ON bedrock_integration.bedrock_kb USING hnsw (embedding vector_cosine_ops) WITH (ef_construction=256);"
    ]

    print("Connecting to the database")
    conn = psycopg2.connect(database=database_name,
                            host=host,
                            user=user,
                            password=password,
                            port=port)
    conn.cursor()
    print("Connected to the database")

    for statement in sql_statements_to_setup_bedrock_kb:
        print(f"Executing: {statement}")
        with conn.cursor() as cur:
            cur.execute(statement)
            conn.commit()
    print("Setup rds for bedrock kb completed")
    conn.close()

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

def lambda_handler(event, context):
    # Your post-deployment logic here
    print("Post-deployment trigger executed")

    print(f"event: {event}")
    print(f"context: {context}")

    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    elif event['RequestType'] == 'Create':

        resource_properties = event['ResourceProperties']
        setup_rds(
            database_name=resource_properties["DATABASE_NAME"],
            host=resource_properties["HOST"],
            user=resource_properties["USER"],
            password=json.loads(get_secret(resource_properties.get('SECRET_NAME')))['password'],
            port=resource_properties["PORT"]
        )

        setup_bedrock_kb(
            credentials_secret_arn=resource_properties["SECRET_NAME"],
            database_name=resource_properties["DATABASE_NAME"],
            aurora_cluster_arn=resource_properties["HOST"],
            table_name="bedrock_integration.bedrock_kb"
        )

        token = ("%s.%s" % (id_generator(6), id_generator(16)))
        responseData = {}
        responseData['Token'] = token
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)
        return token
    elif event['RequestType'] == 'Update':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    else:
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

