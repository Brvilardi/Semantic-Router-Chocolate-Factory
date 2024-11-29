import aws_cdk
from aws_cdk import (
    Stack, aws_dynamodb
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







