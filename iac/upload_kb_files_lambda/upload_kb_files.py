import os
import boto3
import cfnresponse
import string
import random

def id_generator(size, chars=string.ascii_lowercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))

def lambda_handler(event, context):
    print(f'Event: {event}')
    try:
        token = ("%s.%s" % (id_generator(6), id_generator(16)))
        responseData = {}
        responseData['Token'] = token

        if event['RequestType'] == 'Delete':
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(os.environ['BUCKET_NAME'])
            for obj in bucket.objects.filter():
                print(f"Object {obj} being deleted...")
                s3.Object(bucket.name, obj.key).delete()
                bucket.object_versions.filter(Prefix=obj.key).delete()
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

        elif event['RequestType'] == 'Update':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

        elif event['RequestType'] == 'Create':
            file_names = os.listdir('files')
            s3_client = boto3.client('s3')
            bucket_name = os.environ['BUCKET_NAME']

            for file in file_names:
                print(f'Uploading {file} to {bucket_name}')
                s3_client.upload_file(f'files/{file}', bucket_name, file)
            print('Upload complete')
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)

        else:
            cfnresponse.send(event, context, cfnresponse.FAILED, {})
        return token

    except Exception as e:
        print(f'Exception: {e}')
        cfnresponse.send(event, context, cfnresponse.FAILED, e.__str__())
        return None