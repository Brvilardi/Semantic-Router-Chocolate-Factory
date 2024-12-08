import aws_cdk
from aws_cdk import (
    Stack, aws_dynamodb, aws_stepfunctions, cloudformation_include, aws_lambda
)
from constructs import Construct

from .kb_component import KnowledgeBase
from .network_component import VPC


class ChocolateFactoryChatbot(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.dynamodb_table = aws_dynamodb.Table(
            self,
            "DynamoTable",
            partition_key=aws_dynamodb.Attribute(
                name="pk",
                type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="sk",
                type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY
        )

        self.vpc = VPC(self)

        self.knowledge_base = KnowledgeBase(self, vpc=self.vpc.vpc)

        self.update_dynamo_summary_state_machine = cloudformation_include.CfnInclude(
            self,
            "UpdateDynamoSummaryStateMachine",
            template_file="./state_machines/update_dynamo_summary.yaml"
        )


        self.chocolate_factory_state_machine = cloudformation_include.CfnInclude(
            self,
            "ChocolateFactoryStateMachine",
            template_file="./state_machines/chocolate_factory.yaml"
        )

        self.api_lambda = aws_lambda.Function(
            self,
            "ChocolateFactpryApiLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            handler="api.lambda_handler",
            code=aws_lambda.Code.from_asset("../back-end"),
            timeout=aws_cdk.Duration.seconds(15),
            environment={
                "CHAT_TABLE_NAME": self.dynamodb_table.table_name,
                "STEP_FUNCTIONS_ARN": "arn:aws:states:us-east-1:667078243530:express:StateMachinef45946c0:27d36d4a-f9e9-4880-a29e-c698baaf362f:4fcd1d39-f8bc-40c6-8b30-c94b7a3388c7",
                "KNOWLEDGE_BASE_ID": self.knowledge_base.knowledge_base.attr_knowledge_base_id
            }
        )






        aws_cdk.CfnOutput(self, "AuroraClusterArn",
                          export_name="AuroraClusterArn",
                          value=self.knowledge_base.aurora_serverless_v2.cluster_arn)

        aws_cdk.CfnOutput(self, "SecretArn",
                            export_name="SecretArn",
                            value=self.knowledge_base.aurora_serverless_v2.secret.secret_arn)

        aws_cdk.CfnOutput(self, "DatabaseName",
                            export_name="DatabaseName",
                            value="postgres")

        aws_cdk.CfnOutput(self, "TableName",
                            export_name="TableName",
                            value="bedrock_integration.bedrock_kb")

        aws_cdk.CfnOutput(self, "DynamoTableName",
                          export_name="DynamoTableName",
                          value=self.dynamodb_table.table_name)







