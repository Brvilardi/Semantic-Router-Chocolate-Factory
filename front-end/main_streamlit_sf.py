import json
import boto3
from re import IGNORECASE, match
from sys import argv

import streamlit as st
from streamlit.runtime import get_instance
from streamlit.runtime.scriptrunner import get_script_run_ctx

if argv[1] != "--step-function-arn" or not match(
    "arn:aws:states:[a-z]{2}-[a-z]+-[0-9]:([0-9]{12}):stateMachine:.+",
    argv[2],
    IGNORECASE,
):
    print("Invalid arg or ARN. Usage: streamlit run <script.py> -- --step-function-arn <step-function-arn>")
    exit(1)

STEP_FUNCTION_ARN = argv[2]

step_functions = boto3.client('stepfunctions')


def invoke_step_function(question, session_id):
    payload = {
        "user_input": question,
        "session_id": session_id,
    }

    response = step_functions.start_sync_execution(
        stateMachineArn=STEP_FUNCTION_ARN,
        input=json.dumps(payload)
    )
    from pprint import pprint

    pprint(response)

    if response['status'] == 'FAILED':
        raise Exception(response['cause'])

    output = json.loads(response['output'])
    response = output["response"]
    answer_time = output["workflow_execution_time"]

    return response, answer_time


def get_chat_session():
    runtime = get_instance()
    session_id = get_script_run_ctx().session_id
    session_info = runtime._session_mgr.get_session_info(session_id)
    if session_info is None:
        raise RuntimeError("Couldn't get your Streamlit Session object.")
    return session_info.session.id


st.title(f"GeniusAI - Willy Wonka 🏭🍫")

st.logo("genius_ai.png")

st.markdown(
        "<div style='background-color: #8EB69B; padding: 10px; border-radius: 10px; text-align: center;'>"
        "<img src='https://d335luupugsy2.cloudfront.net/cms/files/725547/1726145377/$gqwjb4k5ujw'"
        "width='150px' style='margin-bottom: 10px;'>"
        "<h2 style='color: white;'>Atendimento de Suporte - Willy Wonka</h2>"
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

            resp = invoke_step_function(
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
            status.write(f"Duração: {answer_time}")
            status.write(f"Rota: {response['route']}")
            status.write(f"Resumo: {response['summary']}")
            status.write(f"Session ID: {session_id}")

    st.session_state.messages.append({"role": "assistant", "content": response["model_response"]})