import json
import os
from pprint import pprint
from sys import getsizeof

import boto3

# configuration = {
#     'chat_table_name': os.environ['CHAT_TABLE_NAME'],
#     'update_chat_history_stepfunction': os.environ['STEP_FUNCTIONS_ARN'],
#     'knowledge_base_id': os.environ['KNOWLEDGE_BASE_ID'],
# }



configuration = {
    'chat_table_name': "chocolate-factory-chatbot-DynamoTableB2B22E15-OQYZ492LZMU0",
    'update_chat_history_stepfunction': "arn:aws:states:us-east-1:667078243530:stateMachine:StateMachined9c8d049",
    'knowledge_base_id': "ABWXMDXUBA",
}

prompts = {}

directory_contents = os.listdir('prompt')
prompt_directories = []
single_prompt_files = []

# gets all the directories with prompts inside and the single files
for content in directory_contents:
    print("\n\n")
    full_path = os.path.join('prompt', content)
    if os.path.isdir(full_path): #it is a directory
        print(f"Getting prompts from {content}")
        prompts[content] = {}
        for file in os.listdir(full_path): # gets all files
            if ".txt" in file:
                print(f"Loading {file}")
                file_name = file.split(".")[0]
                prompts[content][file_name] = {}
                with open(f'prompt/{content}/{file}') as f:
                    prompts[content][file_name]['system'] = f.read() # read the content of the file and store it in the dictionary
                    print(f"Sample: {prompts[content][file_name]['system'][:50]}")

    if ".txt" in content:
        print(f"Loading {file}")
        file_name = content.split(".")[0]
        prompts[file_name] = {}
        with open(f'prompt/{content}') as f:
            prompts[file_name]['system'] = f.read()



configuration = configuration | prompts # merge the two dictionaries

step_function_client = boto3.client('stepfunctions')


def lambda_handler(event, context):

    body = json.loads(event['body'])
    if not body.get('user_input') or not body.get('session_id'):
        return {
            'statusCode': 400,
            'body': json.dumps('No user input provided')
        }

    user_input = body['user_input']
    session_id = body.get('session_id')


    response = step_function_client.start_sync_execution(
        stateMachineArn="arn:aws:states:us-east-1:667078243530:stateMachine:StateMachinef45946c0",
        input=json.dumps({
            'user_input': user_input,
            'session_id': session_id,
            'configuration': configuration
        })
    )
    print(response)








