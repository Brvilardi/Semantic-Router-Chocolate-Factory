import psycopg2
import os
import boto3
from botocore.exceptions import ClientError
import json

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


DATABASE_NAME = os.environ.get("DATABASE_NAME")
HOST = os.environ.get("HOST")
USER = os.environ.get("USER")
PASSWORD = json.loads(get_secret(os.environ.get("SECRET_NAME")))["password"]
PORT = os.environ.get("PORT")


sql_statements_to_setup_bedrock_kb = [
    "CREATE EXTENSION IF NOT EXISTS vector;",
    "SELECT extversion FROM pg_extension WHERE extname='vector';",
    "CREATE SCHEMA bedrock_integration;",
    f"CREATE ROLE bedrock_user WITH PASSWORD '{PASSWORD}' LOGIN;",
    "GRANT ALL ON SCHEMA bedrock_integration to bedrock_user;",
    "CREATE TABLE bedrock_integration.bedrock_kb (id uuid PRIMARY KEY, embedding vector(1024), chunks text, metadata json);",
    "CREATE INDEX ON bedrock_integration.bedrock_kb USING hnsw (embedding vector_cosine_ops) WITH (ef_construction=256);"


]

def lambda_handler(event, context):
    print("Connecting to the database")
    conn = psycopg2.connect(database=DATABASE_NAME,
                            host=HOST,
                            user=USER,
                            password=PASSWORD,
                            port=PORT)
    conn.cursor()
    print("Connected to the database")

    for statement in sql_statements_to_setup_bedrock_kb:
        print(f"Executing: {statement}")
        with conn.cursor() as cur:
            cur.execute(statement)
            conn.commit()
    conn.close()


    return {
        'statusCode': 200,
        'body': "Aurora postgres ready to use for bedrock kb"
    }





