import aws_cdk as core
import aws_cdk.assertions as assertions

from iac.iac_stack import IacStack

# example tests. To run these tests, uncomment this file along with the example
# resource in iac/iac_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = IacStack(app, "iac")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
