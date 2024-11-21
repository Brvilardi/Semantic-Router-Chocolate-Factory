#!/usr/bin/env python3
import os

import aws_cdk as cdk

from iac.iac_stack import ChocolateFactoryChatbot
from setup_bedrock_kb import setup_bedrock_kb


app = cdk.App()

chocolate_factory_stack = ChocolateFactoryChatbot(app, "chocolate-factory-chatbot-genai",
    env=cdk.Environment(account='667078243530', region='us-east-1'),
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()

print(chocolate_factory_stack)


# setup_bedrock_kb(
#     setup_rds_lambda_arn=chocolate_factory_stack.setup_rds_lambda.function_arn,
#     credentials_secret_arn=chocolate_factory_stack.aurora_serverless_v2.secret.secret_arn,
#     database_name="postgres",
#     aurora_cluster_arn=chocolate_factory_stack.aurora_serverless_v2.cluster_arn,
#     table_name="bedrock_integration.bedrock_kb"
# )

