import tiktoken
import openai
import os
import requests
import time
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType

#AZURE_STORAGE_ACCOUNT = "account namex"
#AZURE_STORAGE_CONTAINER = "container name"
#AZURE_SEARCH_SERVICE = "search service name"
#AZURE_SEARCH_INDEX = "search index"

openai.api_type = "azure"
openai.api_version = "2023-03-15-preview" 
openai.api_base = "https://a11ygenerative.openai.azure.com/" # Your Azure OpenAI resource's endpoint value .
openai.api_key = "eb9be520bbb44c1ba2c531e2fe78574c"

# You might need to change these fields based on your search service config
KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "Story"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "Keywords"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "Titles"

azure_credential = DefaultAzureCredential()

search_client = SearchClient(
    endpoint=f"https://datapacificsemanticsearch.search.windows.net",
    index_name="datapacificindex",
    credential=AzureKeyCredential("swr6mVKwaB4jBXB6EMPt6uWYn9TESLNvAgJxNzEC8CAzSeCfwA7s"))

system_message = {"role": "system", "content": """
Assistant helps answer questions from a predefined list of sources. 
Answer ONLY with the facts listed in the list of sources given to you. If there isn't enough information, say you don't know. Do not generate answers that don't use the sources given to you. If asking a clarifying question to the user would help, ask the question. 
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
"""}

max_response_tokens = 1000
token_limit= 8000

conversation = []
conversation.append(system_message)

def num_tokens_from_messages(messages, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens
    
def get_response(search):

    print("Searching:", search)

    r = search_client.search(search, query_type="semantic", query_language="en-us", query_speller="lexicon", semantic_configuration_name="datapacificsemanticconfig", top=3)
    results = [doc[KB_FIELDS_SOURCEPAGE] + ": " + doc[KB_FIELDS_CONTENT].replace("\n", "").replace("\r", "") for doc in r]
    content = "\n".join(results)

    search_sources = {"role": "system", "content": content}
    conversation.append(search_sources)
    conversation.append({"role": "user", "content": search})
    conv_history_tokens = num_tokens_from_messages(conversation)

    while (conv_history_tokens+max_response_tokens >= token_limit):
        del conversation[1] 
        conv_history_tokens = num_tokens_from_messages(conversation)
    
    response = openai.ChatCompletion.create(
        engine="a11y8k", # The deployment name you chose when you deployed the ChatGPT or GPT-4 model.
        messages = conversation,
        temperature=.7,
        max_tokens=1000,
    )

    conversation.append({"role": "assistant", "content": response['choices'][0]['message']['content']})
    print("\n" + response['choices'][0]['message']['content'] + "\n")
    return("\n" + response['choices'][0]['message']['content'] + "\n")      
    

    