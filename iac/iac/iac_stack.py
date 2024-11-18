from idlelib.help_about import version
from uuid import uuid4

import aws_cdk
from aws_cdk import (
    # Duration,
    Stack, aws_dynamodb, aws_s3, aws_rds, Duration, aws_lambda, aws_iam, aws_ec2
    # aws_sqs as sqs,
)

from aws_cdk import triggers

from aws_cdk.aws_secretsmanager import Secret, SecretStringGenerator
from constructs import Construct


class ChocolateFactoryChatbot(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.random_value = "12345n"

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
            versioned=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY
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

        self.vpc = aws_ec2.Vpc(
            self, "GenAIChatVPC",
            # nat_gateways=0,
            # subnet_configuration=[
            #     aws_cdk.aws_ec2.SubnetConfiguration(
            #         subnet_type=aws_cdk.aws_ec2.SubnetType.PRIVATE_ISOLATED,
            #         name="DatabaseSubnet",
            #         cidr_mask=28
            #     )
            # ]

        )

        self.vpc.apply_removal_policy(aws_cdk.RemovalPolicy.DESTROY)

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

        self.post_deploy_function = aws_lambda.Function(
            self,
            "PostDeployFunction",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="setup_kb.lambda_handler",
            code=aws_lambda.Code.from_asset("./setup_kb_lambda",
                                            # bundling={
                                            #     "image": aws_lambda.Runtime.PYTHON_3_9.bundling_image,
                                            #     "command": [
                                            #         'bash', '-c',
                                            #         'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
                                            #     ]},
                                            ),
            memory_size=1024,
            timeout=Duration.seconds(30),
        )


        # self.post_deploy_trigger = triggers.Trigger(
        #     self,
        #     "PostDeployTrigger",
        #     handler=self.post_deploy_function,
        #     execute_after=[self.setup_rds_lambda, self.aurora_serverless_v2, self.post_deploy_function]
        # )

        aws_cdk.CustomResource(
            self,
            "PostDeployResource",
            service_token=self.post_deploy_function.function_arn,
            properties={
                "DATABASE_NAME": "postgres",
                "HOST": self.aurora_serverless_v2.cluster_endpoint.hostname,
                "USER": "postgres",
                "SECRET_NAME": self.aurora_serverless_v2.secret.secret_name,
                "PORT": "5432"
            }
        )

        aws_cdk.CfnOutput(self, "AuroraClusterArn",
                          export_name="AuroraClusterArn",
                          value=self.aurora_serverless_v2.cluster_arn)

        aws_cdk.CfnOutput(self, "LambdaSetupRdsArn",
                            export_name="LambdaSetupRdsArn",
                            value=self.setup_rds_lambda.function_arn)

        aws_cdk.CfnOutput(self, "SecretArn",
                            export_name="SecretArn",
                            value=self.aurora_serverless_v2.secret.secret_arn)

        aws_cdk.CfnOutput(self, "DatabaseName",
                            export_name="DatabaseName",
                            value="postgres")

        aws_cdk.CfnOutput(self, "TableName",
                            export_name="TableName",
                            value="bedrock_integration.bedrock_kb")







