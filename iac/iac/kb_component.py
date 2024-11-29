from aws_cdk import (
    aws_lambda as lambda_, aws_s3, aws_lambda, aws_rds,
    NestedStack, Duration, aws_ec2, aws_bedrock, aws_iam, aws_logs
)
from constructs import Construct

import aws_cdk

class KnowledgeBase(Construct):

    def __init__(self, scope: Construct, vpc: aws_ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, "KnowledgeBase")

        self.data_source_bucket = aws_s3.Bucket(
            self,
            "DataSourceBucket",
            versioned=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY
        )

        self.upload_kb_files_function = aws_lambda.Function(
            self,
            "UploadKBFilesFunction",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="upload_kb_files.lambda_handler",
            code=aws_lambda.Code.from_asset("./upload_kb_files_lambda",
                                            bundling={
                                                "image": aws_lambda.Runtime.PYTHON_3_9.bundling_image,
                                                "command": [
                                                    'bash', '-c',
                                                    'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
                                                ]}
                                            ),
            memory_size=1024,
            timeout=Duration.seconds(30),
            environment={
                "BUCKET_NAME": self.data_source_bucket.bucket_name
            }
        )

        self.data_source_bucket.grant_read_write(self.upload_kb_files_function)
        self.upload_kb_files_function.node.add_dependency(self.data_source_bucket)

        self.upload_kb_files_resource = aws_cdk.CustomResource(
            self,
            "UploadKBFilesResource",
            service_token=self.upload_kb_files_function.function_arn,
            properties={}
        )

        self.aurora_serverless_v2 = aws_rds.DatabaseCluster(self, "VectorDataBase",
                                                            engine=aws_rds.DatabaseClusterEngine.aurora_postgres(
                                                                version=aws_rds.AuroraPostgresEngineVersion.VER_16_2),
                                                            serverless_v2_min_capacity=0.5,
                                                            serverless_v2_max_capacity=2,
                                                            writer=aws_rds.ClusterInstance.serverless_v2("writer"),
                                                            vpc=vpc,
                                                            vpc_subnets=aws_ec2.SubnetSelection(
                                                                subnet_type=aws_ec2.SubnetType.PRIVATE_ISOLATED),
                                                            enable_data_api=True,
                                                            credentials=aws_rds.Credentials.from_generated_secret(
                                                                'postgres')
                                                            )

        self.post_deploy_function = aws_lambda.Function(
            self,
            "PostDeployFunction",
            vpc=vpc,
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="setup_kb.lambda_handler",
            code=aws_lambda.Code.from_asset("./setup_kb_lambda",
                                            bundling={
                                                "image": aws_lambda.Runtime.PYTHON_3_9.bundling_image,
                                                "command": [
                                                    'bash', '-c',
                                                    'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
                                                ]},
                                            ),
            memory_size=1024,
            timeout=Duration.seconds(30)
        )

        self.post_deploy_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[self.aurora_serverless_v2.secret.secret_arn]
            )
        )

        self.aurora_serverless_v2.connections.allow_from(self.post_deploy_function, aws_ec2.Port.tcp(5432))

        self.post_deploy_resource = aws_cdk.CustomResource(
            self,
            "PostDeployResource",
            service_token=self.post_deploy_function.function_arn,
            properties={
                "DATABASE_NAME": "postgres",
                "HOST": self.aurora_serverless_v2.cluster_endpoint.hostname,
                "USER": "postgres",
                "SECRET_NAME": self.aurora_serverless_v2.secret.secret_name,
                "PORT": "5432"
            },
            removal_policy=aws_cdk.RemovalPolicy.RETAIN #I was not able to fix the deletion issue on lambda, where the .send method was not reaching the CloudFormation API for some reason (on CREATE it reaches)
        )

        self.post_deploy_resource.node.add_dependency(self.aurora_serverless_v2)

        self.kb_iam_role = aws_iam.Role(
            self,
            "KBRole",
            assumed_by=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        self.kb_iam_policy = aws_iam.Policy(
            self,
            "KBPolicy",
            policy_name="KBPolicy",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["rds-data:BatchExecuteStatement",
                             "rds-data:ExecuteStatement",
                             "rds:DescribeDBClusters"
                             ],
                    resources=[self.aurora_serverless_v2.cluster_arn]
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["secretsmanager:GetSecretValue",
                             "kms:GenerateDataKey",
                             "kms:Decrypt"
                             ],
                    resources=[self.aurora_serverless_v2.secret.secret_arn]
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["s3:GetObject", "s3:ListBucket"],
                    resources=[self.data_source_bucket.bucket_arn, f"{self.data_source_bucket.bucket_arn}/*"]
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["bedrock:ListFoundationModels", "bedrock:ListCustomModels"],
                    resources=["*"]
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["bedrock:InvokeModel"],
                    resources=[f"arn:aws:bedrock:*"]
                )
            ]
        )

        self.kb_iam_policy.attach_to_role(self.kb_iam_role)

        self.knowledge_base = aws_bedrock.CfnKnowledgeBase(
            self,
            "KnowledgeBase",
            name="ChocolateFactoryKB",
            description="Knowledge base for Chocolate Factory",
            role_arn=self.kb_iam_role.role_arn,
            knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0",
                )
            ),
            storage_configuration=aws_bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="RDS",
                rds_configuration=aws_bedrock.CfnKnowledgeBase.RdsConfigurationProperty(
                    credentials_secret_arn=self.aurora_serverless_v2.secret.secret_arn,
                    database_name="postgres",  # TODO use global variable
                    field_mapping=aws_bedrock.CfnKnowledgeBase.RdsFieldMappingProperty(
                        metadata_field="metadata",
                        primary_key_field="id",
                        text_field="chunks",
                        vector_field="embedding"
                    ),
                    resource_arn=self.aurora_serverless_v2.cluster_arn,
                    table_name="bedrock_integration.bedrock_kb"  # TODO use global variable
                )
            )
        )

        self.knowledge_base.node.add_dependency(self.kb_iam_policy)
        self.knowledge_base.node.add_dependency(self.post_deploy_resource)

        self.knowledge_base_data_source = aws_bedrock.CfnDataSource(
            self,
            "KnowledgeBaseDataSource",
            name="ChocolateFactoryDataSource",
            description="Data source for Chocolate Factory",
            data_source_configuration=aws_bedrock.CfnDataSource.DataSourceConfigurationProperty(
                s3_configuration=aws_bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=self.data_source_bucket.bucket_arn
                ),
                type="S3"
            ),
            knowledge_base_id=self.knowledge_base.get_att("KnowledgeBaseId").to_string()
        )

        self.start_kb_sync = aws_cdk.custom_resources.AwsCustomResource(
            self,
            "StartKBSync",
            on_create=aws_cdk.custom_resources.AwsSdkCall(
                service="bedrock-agent",
                action="StartIngestionJob",
                parameters={
                    "knowledgeBaseId": self.knowledge_base.get_att("KnowledgeBaseId").to_string(),
                    "dataSourceId": self.knowledge_base_data_source.get_att("DataSourceId").to_string()

                },
                physical_resource_id=aws_cdk.custom_resources.PhysicalResourceId.of("StartKBSync")
            ),
            policy=aws_cdk.custom_resources.AwsCustomResourcePolicy.from_sdk_calls(
                resources=aws_cdk.custom_resources.AwsCustomResourcePolicy.ANY_RESOURCE
            )
        )

        self.start_kb_sync.node.add_dependency(self.knowledge_base_data_source)
        self.start_kb_sync.node.add_dependency(self.upload_kb_files_resource)
