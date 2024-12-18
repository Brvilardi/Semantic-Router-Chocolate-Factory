
import aws_cdk
from aws_cdk import (
    aws_ec2, cloudformation_include, aws_dynamodb, aws_iam
)
from aws_cdk.aws_logs import LogGroup
from constructs import Construct
from .kb_component import KnowledgeBase

class StateMachines(Construct):

    def __init__(self, scope: Construct, dynamo_table: aws_dynamodb.Table, knowledge_base: KnowledgeBase,**kwargs) -> None:
        super().__init__(scope, "StateMachines")

        self.dynamo_table_log_group = LogGroup(
            self,
            "DynamoTableLogGroup",
            removal_policy=aws_cdk.RemovalPolicy.DESTROY
        )

        self.dynamo_table_role = aws_iam.Role(
            self,
            "DynamoTableRole",
            assumed_by=aws_iam.ServicePrincipal("states.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ],
            inline_policies={
                "LogGroupPolicy": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            actions=[
                                "logs:*",
                            ],
                            effect=aws_iam.Effect.ALLOW,
                            resources=["*"]
                        )
                    ]
                ),
                "DynamoTablePolicy": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            actions=[
                                "dynamodb:PutItem",
                                "dynamodb:GetItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:Query",
                            ],
                            effect=aws_iam.Effect.ALLOW,
                            resources=[dynamo_table.table_arn]
                        )
                    ]
                )
            }
        )

        self.update_dynamo_summary_state_machine = cloudformation_include.CfnInclude(
            self,
            "UpdateDynamoSummaryStateMachine",
            template_file="./state_machines/update_dynamo_summary.yaml",
            parameters={
                "IamRoleArn": self.dynamo_table_role.role_arn,
                "LogGroupArn": self.dynamo_table_log_group.log_group_arn
            }
        )

        self.update_dynamo_summary_state_machine_arn = self.update_dynamo_summary_state_machine.get_resource("CFUpdateDynamoSummary").attr_arn

        self.state_machine_log_group = LogGroup(
            self,
            "StateMachineLogGroup",
            removal_policy=aws_cdk.RemovalPolicy.DESTROY
        )

        self.state_machine_role = aws_iam.Role(
            self,
            "StateMachineRole",
            assumed_by=aws_iam.ServicePrincipal("states.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess"),
            ],
            inline_policies={
                "LogGroupPolicy": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            actions=[
                                "logs:*",
                            ],
                            effect=aws_iam.Effect.ALLOW,
                            resources=["*"]
                        )
                    ]
                ),
                "DynamoTablePolicy": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:Query",
                            ],
                            effect=aws_iam.Effect.ALLOW,
                            resources=[dynamo_table.table_arn]
                        )
                    ]
                ),
                "StepFunctionPolicy": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            actions=[
                                "states:StartExecution",
                            ],
                            effect=aws_iam.Effect.ALLOW,
                            resources=[self.update_dynamo_summary_state_machine_arn]
                        )
                    ]
                )
            }

        )

        self.chocolate_factory_state_machine = cloudformation_include.CfnInclude(
            self,
            "ChocolateFactoryStateMachine",
            template_file="./state_machines/chocolate_factory.yaml",
            parameters={
                "IamRoleArn": self.state_machine_role.role_arn,
                "LogGroupArn": self.state_machine_log_group.log_group_arn
            }

        )

        self.chocolate_factory_state_machine_arn = self.chocolate_factory_state_machine.get_resource("CFChocolateFactory").attr_arn