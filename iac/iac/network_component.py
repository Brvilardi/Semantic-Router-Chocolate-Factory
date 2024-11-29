
import aws_cdk
from aws_cdk import (
    aws_ec2
)
from constructs import Construct


class VPC(Construct):

    def __init__(self, scope: Construct, **kwargs) -> None:
        super().__init__(scope, "VPC")

        self.vpc = aws_ec2.Vpc(
                    self, "GenAIChatVPC",
                    max_azs = 2,
                    nat_gateways = 2,
                    subnet_configuration=[
                        aws_cdk.aws_ec2.SubnetConfiguration(
                            subnet_type=aws_cdk.aws_ec2.SubnetType.PRIVATE_ISOLATED,
                            name="DatabaseSubnet",
                            cidr_mask=22
                        ),
                        aws_cdk.aws_ec2.SubnetConfiguration(
                            subnet_type=aws_cdk.aws_ec2.SubnetType.PUBLIC,
                            name="PublicSubnet",
                            cidr_mask=22
                        )
                    ]

                )

        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=aws_ec2.GatewayVpcEndpointAwsService.S3
        )

        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=aws_ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER
        )

        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=aws_ec2.GatewayVpcEndpointAwsService.DYNAMODB
        )

        self.vpc.apply_removal_policy(aws_cdk.RemovalPolicy.DESTROY)