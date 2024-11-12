from idlelib.help_about import version
from uuid import uuid4

import aws_cdk
from aws_cdk import (
    # Duration,
    Stack, aws_dynamodb, aws_s3, aws_rds, Duration
    # aws_sqs as sqs,
)
from aws_cdk.aws_secretsmanager import Secret, SecretStringGenerator
from constructs import Construct


class IacStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.random_value = str(uuid4())[:5]

        self.dynamodb_table = aws_dynamodb.Table(
            self,
            "DynamoTable",
            table_name=f"GenAIChatTable-{self.random_value}",
            partition_key=aws_dynamodb.Attribute(
                name="pk",
                type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="sk",
                type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST
        )

        self.data_source_bucket = aws_s3.Bucket(
            self,
            "DataSourceBucket",
            bucket_name=f"gen-ai-knowledgebase-{self.random_value}",
            versioned=True
        )

        self.database_password = Secret(
            self,
            "DatabaseSecret",
            secret_name=f"gen-ai-database-secret-{self.random_value}",
            generate_secret_string=SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                generate_string_key="password"
            )
        )

        self.database_secret = aws_rds.Credentials.from_secret(self.database_password)

        self.vpc = aws_cdk.aws_ec2.Vpc(
            self, "GenAIChatVPC",
        )

        self.aurora_serverless_v2 = aws_rds.DatabaseCluster(self, "Database",
                                                            engine=aws_rds.DatabaseClusterEngine.aurora_postgres(
                                                                version=aws_rds.AuroraPostgresEngineVersion.VER_15_5),
                                                            serverless_v2_min_capacity=0.5,
                                                            serverless_v2_max_capacity=2,
                                                            writer=aws_rds.ClusterInstance.serverless_v2("writer"),
                                                            vpc=self.vpc
                                                            )
