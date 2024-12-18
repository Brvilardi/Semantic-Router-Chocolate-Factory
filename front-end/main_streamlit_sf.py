import json
import boto3
from re import IGNORECASE, match
from sys import argv

import streamlit as st
from streamlit.runtime import get_instance
from streamlit.runtime.scriptrunner import get_script_run_ctx

if argv[1] != "--lambda-function-arn" or not match(
    "arn:aws:lambda:[a-z]{2}-[a-z]+-[0-9]:([0-9]{12}):function:.+",
    argv[2],
    IGNORECASE,
):
    print("Invalid arg or ARN. Usage: streamlit run <script.py> -- --lambda-function-arn <step-function-arn>")
    exit(1)

LAMBDA_FUNCTION_ARN = argv[2]

aws_lambda = boto3.client('lambda', region_name='us-east-1')


def invoke_lambda_function(question, session_id):
    payload = {
        "user_input": question,
        "session_id": session_id,
    }

    lambda_response = aws_lambda.invoke(
        FunctionName=LAMBDA_FUNCTION_ARN,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )

    from pprint import pprint

    pprint(lambda_response)

    if lambda_response['StatusCode'] != 200:
        raise Exception(lambda_response)

    payload = json.loads(lambda_response['Payload'].read())
    body = json.loads(payload['body'])
    print("output: ", payload)
    print(payload.get('statusCode'))
    answer_time = body["workflow_execution_time"]

    return body, answer_time


def get_chat_session():
    runtime = get_instance()
    session_id = get_script_run_ctx().session_id
    session_info = runtime._session_mgr.get_session_info(session_id)
    if session_info is None:
        raise RuntimeError("Couldn't get your Streamlit Session object.")
    return session_info.session.id

st.set_page_config(
    page_title="Chocolate Factory",
    page_icon="logo.jpeg"
)


st.title(f"Semantic Router - Chocolate Factory 🏭🍫")

# st.logo("logo.jpeg")

st.image("logo.jpeg", width=300)

st.markdown(
        "<div style='background-color: #8EB69B; padding: 10px; border-radius: 10px; text-align: center;'>"
        "<h2 style='color: white;'>Atendimento de Suporte - Fábrica de chocolate</h2>"
        "<p style='color: white;'>Seu canal de suporte para Fantástica Fábrica de Chocolates. Fique a vontade para realizar pedidos e tirar dúvidas técnicas! 👋</p4>"
        "<h5 style='color: white;'>Powered by Amazon Bedrock and AWS Step Functions</h5>"
        "</div>",
        unsafe_allow_html=True,
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input("Faça sua pergunta"):
    with st.chat_message("user"):
        st.markdown(question)

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        with st.status("Escrevendo ...", expanded=False) as status:

            session_id = get_chat_session()

            print("Session ID: ", session_id)

            resp = invoke_lambda_function(
                question, session_id
            )

            response, answer_time = resp

            print("answer: ", response["model_response"])

            message_placeholder.markdown(response["model_response"])

            status.update(
                label=f"Respondido!",
                state="complete",
                expanded=False,
            )

            # status.write(f"Custo: US${answer['response_pricing']['price']}")
            status.write(f"Tempo de execução: {answer_time/1000} segundos")
            status.write(f"Rota: {response['route']}")
            status.write(f"Resumo: {response['summary']}")
            status.write(f"Session ID: {session_id}")

    st.session_state.messages.append({"role": "assistant", "content": response["model_response"]})