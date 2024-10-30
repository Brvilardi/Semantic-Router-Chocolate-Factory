# Semantic-Router-Chocolate-Factory

## Introdução
Esse repositório descreve a demo apresentada durante a capacitação do evento AWS GeniusAI.

## Configuração
Para configurar a demo, são necessários alguns passos:

1. Criar tabela no DynamoDB
2. Importar as 2 Step Functions
3. Criar Bucket S3 para base de conhecimento
4. Criar base de conhecimento do Bedrock Knowledge Bases
5. Atualizar KnowledgeBaseID e TableName no StepFunctions
6. Executar o streamlit
   1. streamlit run main_streamlit_sf.py -- --step-function-arn XXXX

