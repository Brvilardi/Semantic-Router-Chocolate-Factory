import cfnresponse
import string
import random

def id_generator(size, chars=string.ascii_lowercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))

def lambda_handler(event, context):
    # Your post-deployment logic here
    print("Post-deployment trigger executed")

    print(f"event: {event}")
    print(f"context: {context}")



    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    elif event['RequestType'] == 'Create':
        token = ("%s.%s" % (id_generator(6), id_generator(16)))
        responseData = {}
        responseData['Token'] = token
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)
        return token
    elif event['RequestType'] == 'Update':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    else:
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

