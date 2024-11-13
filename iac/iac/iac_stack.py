from idlelib.help_about import version
from uuid import uuid4

import aws_cdk
from aws_cdk import (
    # Duration,
    Stack, aws_dynamodb, aws_s3, aws_rds, Duration, aws_lambda, aws_iam, aws_ec2
    # aws_sqs as sqs,
)
from aws_cdk.aws_secretsmanager import Secret, SecretStringGenerator
from constructs import Construct


class ChocolateFactoryChatbot(Stack):

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

        # self.database_password = Secret(
        #     self,
        #     "DatabaseSecret",
        #     secret_name=f"gen-ai-database-secret-{self.random_value}",
        #     generate_secret_string=SecretStringGenerator(
        #         secret_string_template='{"username": "postgres"}',
        #         generate_string_key="password"
        #     )
        # )

        # self.database_secret = aws_rds.Credentials.from_secret(self.database_password)

        self.vpc = aws_cdk.aws_ec2.Vpc(
            self, "GenAIChatVPC",
        )

        self.aurora_serverless_v2 = aws_rds.DatabaseCluster(self, "Database",
                                                            engine=aws_rds.DatabaseClusterEngine.aurora_postgres(
                                                                version=aws_rds.AuroraPostgresEngineVersion.VER_15_5),
                                                            serverless_v2_min_capacity=0.5,
                                                            serverless_v2_max_capacity=2,
                                                            writer=aws_rds.ClusterInstance.serverless_v2("writer"),
                                                            vpc=self.vpc,
                                                            enable_data_api=True,
                                                            credentials=aws_rds.Credentials.from_generated_secret('postgres')
                                                            )

        self.setup_rds_lambda = aws_lambda.Function(
            self,
            "SetupRDSLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="setup_rds_for_kb.lambda_handler",
            code=aws_lambda.Code.from_asset("./setup_rds_lambda",
                                            bundling={
                                                "image":aws_lambda.Runtime.PYTHON_3_9.bundling_image,
                                                "command":[
                                                    'bash', '-c',
                                                    'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
                                                ]},
                                            ),
            memory_size=1024,
            vpc=self.vpc,
            timeout=Duration.seconds(30),
            environment={
                "DATABASE_NAME": "postgres",
                "HOST": self.aurora_serverless_v2.cluster_endpoint.hostname,
                "USER": "postgres",
                "SECRET_NAME": self.aurora_serverless_v2.secret.secret_name,
                "PORT": "5432"
            }
        )

        self.setup_rds_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[self.aurora_serverless_v2.secret.secret_arn]
            )
        )

        #create a connection between aurora and lambda
        self.aurora_serverless_v2.connections.allow_from(self.setup_rds_lambda, aws_ec2.Port.tcp(5432))


