ChatGoogleGenerativeAI
Access Google's Generative AI models, including the Gemini family, directly via the Gemini API or experiment rapidly using Google AI Studio. The langchain-google-genai package provides the LangChain integration for these models. This is often the best starting point for individual developers.

For information on the latest models, their features, context windows, etc. head to the Google AI docs. All examples use the gemini-2.0-flash model. Gemini 2.5 Pro and 2.5 Flash can be used via gemini-2.5-pro-preview-03-25 and gemini-2.5-flash-preview-04-17. All model ids can be found in the Gemini API docs.

Integration details
Class	Package	Local	Serializable	JS support	Package downloads	Package latest
ChatGoogleGenerativeAI	langchain-google-genai	❌	beta	✅	PyPI - Downloads	PyPI - Version
Model features
Tool calling	Structured output	JSON mode	Image input	Audio input	Video input	Token-level streaming	Native async	Token usage	Logprobs
✅	✅	❌	✅	✅	✅	✅	✅	✅	❌
Setup
To access Google AI models you'll need to create a Google Account, get a Google AI API key, and install the langchain-google-genai integration package.

1. Installation:

%pip install -U langchain-google-genai

2. Credentials:

Head to https://ai.google.dev/gemini-api/docs/api-key (or via Google AI Studio) to generate a Google AI API key.

Chat Models
Use the ChatGoogleGenerativeAI class to interact with Google's chat models. See the API reference for full details.

import getpass
import os

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google AI API key: ")

To enable automated tracing of your model calls, set your LangSmith API key:

# os.environ["LANGSMITH_API_KEY"] = getpass.getpass("Enter your LangSmith API key: ")
# os.environ["LANGSMITH_TRACING"] = "true"

Instantiation
Now we can instantiate our model object and generate chat completions:

from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # other params...
)

API Reference:ChatGoogleGenerativeAI
Invocation
messages = [
    (
        "system",
        "You are a helpful assistant that translates English to French. Translate the user sentence.",
    ),
    ("human", "I love programming."),
]
ai_msg = llm.invoke(messages)
ai_msg

AIMessage(content="J'adore la programmation.", additional_kwargs={}, response_metadata={'prompt_feedback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.0-flash', 'safety_ratings': []}, id='run-3b28d4b8-8a62-4e6c-ad4e-b53e6e825749-0', usage_metadata={'input_tokens': 20, 'output_tokens': 7, 'total_tokens': 27, 'input_token_details': {'cache_read': 0}})


print(ai_msg.content)

J'adore la programmation.

Chaining
We can chain our model with a prompt template like so:

from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that translates {input_language} to {output_language}.",
        ),
        ("human", "{input}"),
    ]
)

chain = prompt | llm
chain.invoke(
    {
        "input_language": "English",
        "output_language": "German",
        "input": "I love programming.",
    }
)

API Reference:ChatPromptTemplate
AIMessage(content='Ich liebe Programmieren.', additional_kwargs={}, response_metadata={'prompt_feedback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.0-flash', 'safety_ratings': []}, id='run-e5561c6b-2beb-4411-9210-4796b576a7cd-0', usage_metadata={'input_tokens': 15, 'output_tokens': 7, 'total_tokens': 22, 'input_token_details': {'cache_read': 0}})


Multimodal Usage
Gemini models can accept multimodal inputs (text, images, audio, video) and, for some models, generate multimodal outputs.

Image Input
Provide image inputs along with text using a HumanMessage with a list content format. The gemini-2.0-flash model can handle images.

import base64

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Example using a public URL (remains the same)
message_url = HumanMessage(
    content=[
        {
            "type": "text",
            "text": "Describe the image at the URL.",
        },
        {"type": "image_url", "image_url": "https://picsum.photos/seed/picsum/200/300"},
    ]
)
result_url = llm.invoke([message_url])
print(f"Response for URL image: {result_url.content}")

# Example using a local image file encoded in base64
image_file_path = "/Users/philschmid/projects/google-gemini/langchain/docs/static/img/agents_vs_chains.png"

with open(image_file_path, "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

message_local = HumanMessage(
    content=[
        {"type": "text", "text": "Describe the local image."},
        {"type": "image_url", "image_url": f"data:image/png;base64,{encoded_image}"},
    ]
)
result_local = llm.invoke([message_local])
print(f"Response for local image: {result_local.content}")


API Reference:HumanMessage | ChatGoogleGenerativeAI
Other supported image_url formats:

A Google Cloud Storage URI (gs://...). Ensure the service account has access.
A PIL Image object (the library handles encoding).
Audio Input
Provide audio file inputs along with text. Use a model like gemini-2.0-flash.

import base64

from langchain_core.messages import HumanMessage

# Ensure you have an audio file named 'example_audio.mp3' or provide the correct path.
audio_file_path = "example_audio.mp3"
audio_mime_type = "audio/mpeg"


with open(audio_file_path, "rb") as audio_file:
    encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")

message = HumanMessage(
    content=[
        {"type": "text", "text": "Transcribe the audio."},
        {
            "type": "media",
            "data": encoded_audio,  # Use base64 string directly
            "mime_type": audio_mime_type,
        },
    ]
)
response = llm.invoke([message])  # Uncomment to run
print(f"Response for audio: {response.content}")

API Reference:HumanMessage
Video Input
Provide video file inputs along with text. Use a model like gemini-2.0-flash.

import base64

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Ensure you have a video file named 'example_video.mp4' or provide the correct path.
video_file_path = "example_video.mp4"
video_mime_type = "video/mp4"


with open(video_file_path, "rb") as video_file:
    encoded_video = base64.b64encode(video_file.read()).decode("utf-8")

message = HumanMessage(
    content=[
        {"type": "text", "text": "Describe the first few frames of the video."},
        {
            "type": "media",
            "data": encoded_video,  # Use base64 string directly
            "mime_type": video_mime_type,
        },
    ]
)
response = llm.invoke([message])  # Uncomment to run
print(f"Response for video: {response.content}")

API Reference:HumanMessage | ChatGoogleGenerativeAI
Image Generation (Multimodal Output)
The gemini-2.0-flash model can generate text and images inline (image generation is experimental). You need to specify the desired response_modalities.

import base64

from IPython.display import Image, display
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="models/gemini-2.0-flash-preview-image-generation")

message = {
    "role": "user",
    "content": "Generate a photorealistic image of a cuddly cat wearing a hat.",
}

response = llm.invoke(
    [message],
    generation_config=dict(response_modalities=["TEXT", "IMAGE"]),
)


def _get_image_base64(response: AIMessage) -> None:
    image_block = next(
        block
        for block in response.content
        if isinstance(block, dict) and block.get("image_url")
    )
    return image_block["image_url"].get("url").split(",")[-1]


image_base64 = _get_image_base64(response)
display(Image(data=base64.b64decode(image_base64), width=300))

API Reference:AIMessage | ChatGoogleGenerativeAI


Image and text to image
You can iterate on an image in a multi-turn conversation, as shown below:

next_message = {
    "role": "user",
    "content": "Can you take the same image and make the cat black?",
}

response = llm.invoke(
    [message, response, next_message],
    generation_config=dict(response_modalities=["TEXT", "IMAGE"]),
)

image_base64 = _get_image_base64(response)
display(Image(data=base64.b64decode(image_base64), width=300))



You can also represent an input image and query in a single message by encoding the base64 data in the data URI scheme:

message = {
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": "Can you make this cat orange?",
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_base64}"},
        },
    ],
}

response = llm.invoke(
    [message],
    generation_config=dict(response_modalities=["TEXT", "IMAGE"]),
)

image_base64 = _get_image_base64(response)
display(Image(data=base64.b64decode(image_base64), width=300))



You can also use LangGraph to manage the conversation history for you as in this tutorial.

Tool Calling
You can equip the model with tools to call.

from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI


# Define the tool
@tool(description="Get the current weather in a given location")
def get_weather(location: str) -> str:
    return "It's sunny."


# Initialize the model and bind the tool
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
llm_with_tools = llm.bind_tools([get_weather])

# Invoke the model with a query that should trigger the tool
query = "What's the weather in San Francisco?"
ai_msg = llm_with_tools.invoke(query)

# Check the tool calls in the response
print(ai_msg.tool_calls)

# Example tool call message would be needed here if you were actually running the tool
from langchain_core.messages import ToolMessage

tool_message = ToolMessage(
    content=get_weather(*ai_msg.tool_calls[0]["args"]),
    tool_call_id=ai_msg.tool_calls[0]["id"],
)
llm_with_tools.invoke([ai_msg, tool_message])  # Example of passing tool result back

API Reference:tool | ChatGoogleGenerativeAI | ToolMessage
[{'name': 'get_weather', 'args': {'location': 'San Francisco'}, 'id': 'a6248087-74c5-4b7c-9250-f335e642927c', 'type': 'tool_call'}]


AIMessage(content="OK. It's sunny in San Francisco.", additional_kwargs={}, response_metadata={'prompt_feedback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.0-flash', 'safety_ratings': []}, id='run-ac5bb52c-e244-4c72-9fbc-fb2a9cd7a72e-0', usage_metadata={'input_tokens': 29, 'output_tokens': 11, 'total_tokens': 40, 'input_token_details': {'cache_read': 0}})


Structured Output
Force the model to respond with a specific structure using Pydantic models.

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI


# Define the desired structure
class Person(BaseModel):
    """Information about a person."""

    name: str = Field(..., description="The person's name")
    height_m: float = Field(..., description="The person's height in meters")


# Initialize the model
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
structured_llm = llm.with_structured_output(Person)

# Invoke the model with a query asking for structured information
result = structured_llm.invoke(
    "Who was the 16th president of the USA, and how tall was he in meters?"
)
print(result)

API Reference:ChatGoogleGenerativeAI
name='Abraham Lincoln' height_m=1.93

Token Usage Tracking
Access token usage information from the response metadata.

from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

result = llm.invoke("Explain the concept of prompt engineering in one sentence.")

print(result.content)
print("\nUsage Metadata:")
print(result.usage_metadata)

API Reference:ChatGoogleGenerativeAI
Prompt engineering is the art and science of crafting effective text prompts to elicit desired and accurate responses from large language models.

Usage Metadata:
{'input_tokens': 10, 'output_tokens': 24, 'total_tokens': 34, 'input_token_details': {'cache_read': 0}}


Built-in tools
Google Gemini supports a variety of built-in tools (google search, code execution), which can be bound to the model in the usual way.

from google.ai.generativelanguage_v1beta.types import Tool as GenAITool

resp = llm.invoke(
    "When is the next total solar eclipse in US?",
    tools=[GenAITool(google_search={})],
)

print(resp.content)

The next total solar eclipse visible in the United States will occur on August 23, 2044. However, the path of totality will only pass through Montana, North Dakota, and South Dakota.

For a total solar eclipse that crosses a significant portion of the continental U.S., you'll have to wait until August 12, 2045. This eclipse will start in California and end in Florida.


from google.ai.generativelanguage_v1beta.types import Tool as GenAITool

resp = llm.invoke(
    "What is 2*2, use python",
    tools=[GenAITool(code_execution={})],
)

for c in resp.content:
    if isinstance(c, dict):
        if c["type"] == "code_execution_result":
            print(f"Code execution result: {c['code_execution_result']}")
        elif c["type"] == "executable_code":
            print(f"Executable code: {c['executable_code']}")
    else:
        print(c)

Executable code: print(2*2)

Code execution result: 4

2*2 is 4.
``````output
/Users/philschmid/projects/google-gemini/langchain/.venv/lib/python3.9/site-packages/langchain_google_genai/chat_models.py:580: UserWarning: 
        ⚠️ Warning: Output may vary each run.  
        - 'executable_code': Always present.  
        - 'execution_result' & 'image_url': May be absent for some queries.  

        Validate before using in production.

  warnings.warn(


Native Async
Use asynchronous methods for non-blocking calls.

from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")


async def run_async_calls():
    # Async invoke
    result_ainvoke = await llm.ainvoke("Why is the sky blue?")
    print("Async Invoke Result:", result_ainvoke.content[:50] + "...")

    # Async stream
    print("\nAsync Stream Result:")
    async for chunk in llm.astream(
        "Write a short poem about asynchronous programming."
    ):
        print(chunk.content, end="", flush=True)
    print("\n")

    # Async batch
    results_abatch = await llm.abatch(["What is 1+1?", "What is 2+2?"])
    print("Async Batch Results:", [res.content for res in results_abatch])


await run_async_calls()

API Reference:ChatGoogleGenerativeAI
Async Invoke Result: The sky is blue due to a phenomenon called **Rayle...

Async Stream Result:
The thread is free, it does not wait,
For answers slow, or tasks of fate.
A promise made, a future bright,
It moves ahead, with all its might.

A callback waits, a signal sent,
When data's read, or job is spent.
Non-blocking code, a graceful dance,
Responsive apps, a fleeting glance.

Async Batch Results: ['1 + 1 = 2', '2 + 2 = 4']

Safety Settings
Gemini models have default safety settings that can be overridden. If you are receiving lots of "Safety Warnings" from your models, you can try tweaking the safety_settings attribute of the model. For example, to turn off safety blocking for dangerous content, you can construct your LLM as follows:

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
)

API Reference:ChatGoogleGenerativeAI | HarmBlockThreshold | HarmCategory
For an enumeration of the categories and thresholds available, see Google's safety setting types.

Pinecone
Pinecone is a vector database with broad functionality.

This notebook shows how to use functionality related to the Pinecone vector database.

Setup
To use the PineconeVectorStore you first need to install the partner package, as well as the other packages used throughout this notebook.

pip install -qU langchain langchain-pinecone langchain-openai

Migration note: if you are migrating from the langchain_community.vectorstores implementation of Pinecone, you may need to remove your pinecone-client v2 dependency before installing langchain-pinecone, which relies on pinecone-client v6.

Credentials
Create a new Pinecone account, or sign into your existing one, and create an API key to use in this notebook.

import getpass
import os

from pinecone import Pinecone

if not os.getenv("PINECONE_API_KEY"):
    os.environ["PINECONE_API_KEY"] = getpass.getpass("Enter your Pinecone API key: ")

pinecone_api_key = os.environ.get("PINECONE_API_KEY")

pc = Pinecone(api_key=pinecone_api_key)

If you want to get automated tracing of your model calls you can also set your LangSmith API key by uncommenting below:

# os.environ["LANGSMITH_API_KEY"] = getpass.getpass("Enter your LangSmith API key: ")
# os.environ["LANGSMITH_TRACING"] = "true"

Initialization
Before initializing our vector store, let's connect to a Pinecone index. If one named index_name doesn't exist, it will be created.

from pinecone import ServerlessSpec

index_name = "langchain-test-index"  # change if desired

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)

from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

API Reference:OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

vector_store = PineconeVectorStore(index=index, embedding=embeddings)

Manage vector store
Once you have created your vector store, we can interact with it by adding and deleting different items.

Add items to vector store
We can add items to our vector store by using the add_documents function.

from uuid import uuid4

from langchain_core.documents import Document

document_1 = Document(
    page_content="I had chocolate chip pancakes and scrambled eggs for breakfast this morning.",
    metadata={"source": "tweet"},
)

document_2 = Document(
    page_content="The weather forecast for tomorrow is cloudy and overcast, with a high of 62 degrees.",
    metadata={"source": "news"},
)

document_3 = Document(
    page_content="Building an exciting new project with LangChain - come check it out!",
    metadata={"source": "tweet"},
)

document_4 = Document(
    page_content="Robbers broke into the city bank and stole $1 million in cash.",
    metadata={"source": "news"},
)

document_5 = Document(
    page_content="Wow! That was an amazing movie. I can't wait to see it again.",
    metadata={"source": "tweet"},
)

document_6 = Document(
    page_content="Is the new iPhone worth the price? Read this review to find out.",
    metadata={"source": "website"},
)

document_7 = Document(
    page_content="The top 10 soccer players in the world right now.",
    metadata={"source": "website"},
)

document_8 = Document(
    page_content="LangGraph is the best framework for building stateful, agentic applications!",
    metadata={"source": "tweet"},
)

document_9 = Document(
    page_content="The stock market is down 500 points today due to fears of a recession.",
    metadata={"source": "news"},
)

document_10 = Document(
    page_content="I have a bad feeling I am going to get deleted :(",
    metadata={"source": "tweet"},
)

documents = [
    document_1,
    document_2,
    document_3,
    document_4,
    document_5,
    document_6,
    document_7,
    document_8,
    document_9,
    document_10,
]
uuids = [str(uuid4()) for _ in range(len(documents))]
vector_store.add_documents(documents=documents, ids=uuids)


API Reference:Document
Delete items from vector store
vector_store.delete(ids=[uuids[-1]])

Query vector store
Once your vector store has been created and the relevant documents have been added you will most likely wish to query it during the running of your chain or agent.

Query directly
Performing a simple similarity search can be done as follows:

results = vector_store.similarity_search(
    "LangChain provides abstractions to make working with LLMs easy",
    k=2,
    filter={"source": "tweet"},
)
for res in results:
    print(f"* {res.page_content} [{res.metadata}]")

Similarity search with score
You can also search with score:

results = vector_store.similarity_search_with_score(
    "Will it be hot tomorrow?", k=1, filter={"source": "news"}
)
for res, score in results:
    print(f"* [SIM={score:3f}] {res.page_content} [{res.metadata}]")

Other search methods
There are more search methods (such as MMR) not listed in this notebook, to find all of them be sure to read the API reference.

Query by turning into retriever
You can also transform the vector store into a retriever for easier usage in your chains.

retriever = vector_store.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 1, "score_threshold": 0.4},
)
retriever.invoke("Stealing from the bank is a crime", filter={"source": "news"})

Usage for retrieval-augmented generation
For guides on how to use this vector store for retrieval-augmented generation (RAG), see the following sections


# Google Generative AI Embeddings (AI Studio & Gemini API)
Connect to Google's generative AI embeddings service using the GoogleGenerativeAIEmbeddings class, found in the langchain-google-genai package.

This will help you get started with Google's Generative AI embedding models (like Gemini) using LangChain. For detailed documentation on GoogleGenerativeAIEmbeddings features and configuration options, please refer to the API reference.

Overview
Integration details
Provider	Package
Google Gemini	langchain-google-genai
Setup
To access Google Generative AI embedding models you'll need to create a Google Cloud project, enable the Generative Language API, get an API key, and install the langchain-google-genai integration package.

Credentials
To use Google Generative AI models, you must have an API key. You can create one in Google AI Studio. See the Google documentation for instructions.

Once you have a key, set it as an environment variable GOOGLE_API_KEY:

import getpass
import os

if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API key: ")


Installation
%pip install --upgrade --quiet  langchain-google-genai

Usage
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")
vector = embeddings.embed_query("hello, world!")
vector[:5]

API Reference:GoogleGenerativeAIEmbeddings
[-0.024917153641581535,
 0.012005362659692764,
 -0.003886754624545574,
 -0.05774897709488869,
 0.0020742062479257584]

Batch
You can also embed multiple strings at once for a processing speedup:

vectors = embeddings.embed_documents(
    [
        "Today is Monday",
        "Today is Tuesday",
        "Today is April Fools day",
    ]
)
len(vectors), len(vectors[0])

(3, 3072)

Indexing and Retrieval
Embedding models are often used in retrieval-augmented generation (RAG) flows, both as part of indexing data as well as later retrieving it. For more detailed instructions, please see our RAG tutorials.

Below, see how to index and retrieve data using the embeddings object we initialized above. In this example, we will index and retrieve a sample document in the InMemoryVectorStore.

# Create a vector store with a sample text
from langchain_core.vectorstores import InMemoryVectorStore

text = "LangChain is the framework for building context-aware reasoning applications"

vectorstore = InMemoryVectorStore.from_texts(
    [text],
    embedding=embeddings,
)

# Use the vectorstore as a retriever
retriever = vectorstore.as_retriever()

# Retrieve the most similar text
retrieved_documents = retriever.invoke("What is LangChain?")

# show the retrieved document's content
retrieved_documents[0].page_content

API Reference:InMemoryVectorStore
'LangChain is the framework for building context-aware reasoning applications'

Task type
GoogleGenerativeAIEmbeddings optionally support a task_type, which currently must be one of:

SEMANTIC_SIMILARITY: Used to generate embeddings that are optimized to assess text similarity.
CLASSIFICATION: Used to generate embeddings that are optimized to classify texts according to preset labels.
CLUSTERING: Used to generate embeddings that are optimized to cluster texts based on their similarities.
RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, QUESTION_ANSWERING, and FACT_VERIFICATION: Used to generate embeddings that are optimized for document search or information retrieval.
CODE_RETRIEVAL_QUERY: Used to retrieve a code block based on a natural language query, such as sort an array or reverse a linked list. Embeddings of the code blocks are computed using RETRIEVAL_DOCUMENT.
By default, we use RETRIEVAL_DOCUMENT in the embed_documents method and RETRIEVAL_QUERY in the embed_query method. If you provide a task type, we will use that for all methods.

%pip install --upgrade --quiet  matplotlib scikit-learn

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity

query_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-exp-03-07", task_type="RETRIEVAL_QUERY"
)
doc_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-exp-03-07", task_type="RETRIEVAL_DOCUMENT"
)

q_embed = query_embeddings.embed_query("What is the capital of France?")
d_embed = doc_embeddings.embed_documents(
    ["The capital of France is Paris.", "Philipp is likes to eat pizza."]
)

for i, d in enumerate(d_embed):
    print(f"Document {i+1}:")
    print(f"Cosine similarity with query: {cosine_similarity([q_embed], [d])[0][0]}")
    print("---")

API Reference:GoogleGenerativeAIEmbeddings
Document 1
Cosine similarity with query: 0.7892893360164779
---
Document 2
Cosine similarity with query: 0.5438283285204146
---

Agents¶
Classes:

Name	Description
AgentState	The state of the agent.
Functions:

Name	Description
create_react_agent	Creates an agent graph that calls tools in a loop until a stopping condition is met.
 AgentState ¶
Bases: TypedDict

The state of the agent.

 create_react_agent ¶

create_react_agent(
    model: Union[str, LanguageModelLike],
    tools: Union[
        Sequence[Union[BaseTool, Callable, dict[str, Any]]],
        ToolNode,
    ],
    *,
    prompt: Optional[Prompt] = None,
    response_format: Optional[
        Union[
            StructuredResponseSchema,
            tuple[str, StructuredResponseSchema],
        ]
    ] = None,
    pre_model_hook: Optional[RunnableLike] = None,
    post_model_hook: Optional[RunnableLike] = None,
    state_schema: Optional[StateSchemaType] = None,
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
    version: Literal["v1", "v2"] = "v2",
    name: Optional[str] = None
) -> CompiledStateGraph
Creates an agent graph that calls tools in a loop until a stopping condition is met.

For more details on using create_react_agent, visit Agents documentation.

Parameters:

Name	Type	Description	Default
model	Union[str, LanguageModelLike]	The LangChain chat model that supports tool calling.	required
tools	Union[Sequence[Union[BaseTool, Callable, dict[str, Any]]], ToolNode]	A list of tools or a ToolNode instance. If an empty list is provided, the agent will consist of a single LLM node without tool calling.	required
prompt	Optional[Prompt]	An optional prompt for the LLM. Can take a few different forms:
str: This is converted to a SystemMessage and added to the beginning of the list of messages in state["messages"].
SystemMessage: this is added to the beginning of the list of messages in state["messages"].
Callable: This function should take in full graph state and the output is then passed to the language model.
Runnable: This runnable should take in full graph state and the output is then passed to the language model.
None
response_format	Optional[Union[StructuredResponseSchema, tuple[str, StructuredResponseSchema]]]	An optional schema for the final agent output.
If provided, output will be formatted to match the given schema and returned in the 'structured_response' state key. If not provided, structured_response will not be present in the output state. Can be passed in as:


- an OpenAI function/tool schema,
- a JSON Schema,
- a TypedDict class,
- or a Pydantic class.
- a tuple (prompt, schema), where schema is one of the above.
    The prompt will be used together with the model that is being used to generate the structured response.
Important

response_format requires the model to support .with_structured_output

Note

The graph will make a separate call to the LLM to generate the structured response after the agent loop is finished. This is not the only strategy to get structured responses, see more options in this guide.

None
pre_model_hook	Optional[RunnableLike]	An optional node to add before the agent node (i.e., the node that calls the LLM). Useful for managing long message histories (e.g., message trimming, summarization, etc.). Pre-model hook must be a callable or a runnable that takes in current graph state and returns a state update in the form of

# At least one of `messages` or `llm_input_messages` MUST be provided
{
    # If provided, will UPDATE the `messages` in the state
    "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), ...],
    # If provided, will be used as the input to the LLM,
    # and will NOT UPDATE `messages` in the state
    "llm_input_messages": [...],
    # Any other state keys that need to be propagated
    ...
}
Important

At least one of messages or llm_input_messages MUST be provided and will be used as an input to the agent node. The rest of the keys will be added to the graph state.

Warning

If you are returning messages in the pre-model hook, you should OVERWRITE the messages key by doing the following:


{
    "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *new_messages]
    ...
}
None
post_model_hook	Optional[RunnableLike]	An optional node to add after the agent node (i.e., the node that calls the LLM). Useful for implementing human-in-the-loop, guardrails, validation, or other post-processing. Post-model hook must be a callable or a runnable that takes in current graph state and returns a state update.
Note

Only available with version="v2".

None
state_schema	Optional[StateSchemaType]	An optional state schema that defines graph state. Must have messages and remaining_steps keys. Defaults to AgentState that defines those two keys.	None
config_schema	Optional[Type[Any]]	An optional schema for configuration. Use this to expose configurable parameters via agent.config_specs.	None
checkpointer	Optional[Checkpointer]	An optional checkpoint saver object. This is used for persisting the state of the graph (e.g., as chat memory) for a single thread (e.g., a single conversation).	None
store	Optional[BaseStore]	An optional store object. This is used for persisting data across multiple threads (e.g., multiple conversations / users).	None
interrupt_before	Optional[list[str]]	An optional list of node names to interrupt before. Should be one of the following: "agent", "tools". This is useful if you want to add a user confirmation or other interrupt before taking an action.	None
interrupt_after	Optional[list[str]]	An optional list of node names to interrupt after. Should be one of the following: "agent", "tools". This is useful if you want to return directly or run additional processing on an output.	None
debug	bool	A flag indicating whether to enable debug mode.	False
version	Literal['v1', 'v2']	Determines the version of the graph to create. Can be one of:
"v1": The tool node processes a single message. All tool calls in the message are executed in parallel within the tool node.
"v2": The tool node processes a tool call. Tool calls are distributed across multiple instances of the tool node using the Send API.
'v2'
name	Optional[str]	An optional name for the CompiledStateGraph. This name will be automatically used when adding ReAct agent graph to another graph as a subgraph node - particularly useful for building multi-agent systems.	None
Returns:

Type	Description
CompiledStateGraph	A compiled LangChain runnable that can be used for chat interactions.
The "agent" node calls the language model with the messages list (after applying the prompt). If the resulting AIMessage contains tool_calls, the graph will then call the "tools". The "tools" node executes the tools (1 tool per tool_call) and adds the responses to the messages list as ToolMessage objects. The agent node then calls the language model again. The process repeats until no more tool_calls are present in the response. The agent then returns the full list of messages as a dictionary containing the key "messages".

Tools
LLM
User
Tools
LLM
User
Prompt + LLM
loop
[while tool_calls present]
Initial input
Execute tools
ToolMessage for each tool_calls
Return final state
Example

from langgraph.prebuilt import create_react_agent

def check_weather(location: str) -> str:
    '''Return the weather forecast for the specified location.'''
    return f"It's always sunny in {location}"

graph = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=[check_weather],
    prompt="You are a helpful assistant",
)
inputs = {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
for chunk in graph.stream(inputs, stream_mode="updates"):
    print(chunk)
 ToolNode ¶
Bases: RunnableCallable

A node that runs the tools called in the last AIMessage.

It can be used either in StateGraph with a "messages" state key (or a custom key passed via ToolNode's 'messages_key'). If multiple tool calls are requested, they will be run in parallel. The output will be a list of ToolMessages, one for each tool call.

Tool calls can also be passed directly as a list of ToolCall dicts.

Parameters:

Name	Type	Description	Default
tools	Sequence[Union[BaseTool, Callable]]	A sequence of tools that can be invoked by the ToolNode.	required
name	str	The name of the ToolNode in the graph. Defaults to "tools".	'tools'
tags	Optional[list[str]]	Optional tags to associate with the node. Defaults to None.	None
handle_tool_errors	Union[bool, str, Callable[..., str], tuple[type[Exception], ...]]	How to handle tool errors raised by tools inside the node. Defaults to True. Must be one of the following:
True: all errors will be caught and a ToolMessage with a default error message (TOOL_CALL_ERROR_TEMPLATE) will be returned.
str: all errors will be caught and a ToolMessage with the string value of 'handle_tool_errors' will be returned.
tuple[type[Exception], ...]: exceptions in the tuple will be caught and a ToolMessage with a default error message (TOOL_CALL_ERROR_TEMPLATE) will be returned.
Callable[..., str]: exceptions from the signature of the callable will be caught and a ToolMessage with the string value of the result of the 'handle_tool_errors' callable will be returned.
False: none of the errors raised by the tools will be caught
True
messages_key	str	The state key in the input that contains the list of messages. The same key will be used for the output from the ToolNode. Defaults to "messages".	'messages'
The ToolNode is roughly analogous to:


tools_by_name = {tool.name: tool for tool in tools}
def tool_node(state: dict):
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}
Tool calls can also be passed directly to a ToolNode. This can be useful when using the Send API, e.g., in a conditional edge:


def example_conditional_edge(state: dict) -> List[Send]:
    tool_calls = state["messages"][-1].tool_calls
    # If tools rely on state or store variables (whose values are not generated
    # directly by a model), you can inject them into the tool calls.
    tool_calls = [
        tool_node.inject_tool_args(call, state, store)
        for call in last_message.tool_calls
    ]
    return [Send("tools", [tool_call]) for tool_call in tool_calls]
Important
The input state can be one of the following:
A dict with a messages key containing a list of messages.
A list of messages.
A list of tool calls.
If operating on a message list, the last message must be an AIMessage with tool_calls populated.
Methods:

Name	Description
inject_tool_args	Injects the state and store into the tool call.
 inject_tool_args ¶

inject_tool_args(
    tool_call: ToolCall,
    input: Union[
        list[AnyMessage], dict[str, Any], BaseModel
    ],
    store: Optional[BaseStore],
) -> ToolCall
Injects the state and store into the tool call.

Tool arguments with types annotated as InjectedState and InjectedStore are ignored in tool schemas for generation purposes. This method injects them into tool calls for tool invocation.

Parameters:

Name	Type	Description	Default
tool_call	ToolCall	The tool call to inject state and store into.	required
input	Union[list[AnyMessage], dict[str, Any], BaseModel]	The input state to inject.	required
store	Optional[BaseStore]	The store to inject.	required
Returns:

Name	Type	Description
ToolCall	ToolCall	The tool call with injected state and store.
Classes:

Name	Description
InjectedState	Annotation for a Tool arg that is meant to be populated with the graph state.
InjectedStore	Annotation for a Tool arg that is meant to be populated with LangGraph store.
Functions:

Name	Description
tools_condition	Use in the conditional_edge to route to the ToolNode if the last message
 InjectedState ¶
Bases: InjectedToolArg

Annotation for a Tool arg that is meant to be populated with the graph state.

Any Tool argument annotated with InjectedState will be hidden from a tool-calling model, so that the model doesn't attempt to generate the argument. If using ToolNode, the appropriate graph state field will be automatically injected into the model-generated tool args.

Parameters:

Name	Type	Description	Default
field	Optional[str]	The key from state to insert. If None, the entire state is expected to be passed in.	None
Example

from typing import List
from typing_extensions import Annotated, TypedDict

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import tool

from langgraph.prebuilt import InjectedState, ToolNode


class AgentState(TypedDict):
    messages: List[BaseMessage]
    foo: str

@tool
def state_tool(x: int, state: Annotated[dict, InjectedState]) -> str:
    '''Do something with state.'''
    if len(state["messages"]) > 2:
        return state["foo"] + str(x)
    else:
        return "not enough messages"

@tool
def foo_tool(x: int, foo: Annotated[str, InjectedState("foo")]) -> str:
    '''Do something else with state.'''
    return foo + str(x + 1)

node = ToolNode([state_tool, foo_tool])

tool_call1 = {"name": "state_tool", "args": {"x": 1}, "id": "1", "type": "tool_call"}
tool_call2 = {"name": "foo_tool", "args": {"x": 1}, "id": "2", "type": "tool_call"}
state = {
    "messages": [AIMessage("", tool_calls=[tool_call1, tool_call2])],
    "foo": "bar",
}
node.invoke(state)

[
    ToolMessage(content='not enough messages', name='state_tool', tool_call_id='1'),
    ToolMessage(content='bar2', name='foo_tool', tool_call_id='2')
]
 InjectedStore ¶
Bases: InjectedToolArg

Annotation for a Tool arg that is meant to be populated with LangGraph store.

Any Tool argument annotated with InjectedStore will be hidden from a tool-calling model, so that the model doesn't attempt to generate the argument. If using ToolNode, the appropriate store field will be automatically injected into the model-generated tool args. Note: if a graph is compiled with a store object, the store will be automatically propagated to the tools with InjectedStore args when using ToolNode.

Warning

InjectedStore annotation requires langchain-core >= 0.3.8

Example

from typing import Any
from typing_extensions import Annotated

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import InjectedStore, ToolNode

store = InMemoryStore()
store.put(("values",), "foo", {"bar": 2})

@tool
def store_tool(x: int, my_store: Annotated[Any, InjectedStore()]) -> str:
    '''Do something with store.'''
    stored_value = my_store.get(("values",), "foo").value["bar"]
    return stored_value + x

node = ToolNode([store_tool])

tool_call = {"name": "store_tool", "args": {"x": 1}, "id": "1", "type": "tool_call"}
state = {
    "messages": [AIMessage("", tool_calls=[tool_call])],
}

node.invoke(state, store=store)

{
    "messages": [
        ToolMessage(content='3', name='store_tool', tool_call_id='1'),
    ]
}
 tools_condition ¶

tools_condition(
    state: Union[
        list[AnyMessage], dict[str, Any], BaseModel
    ],
    messages_key: str = "messages",
) -> Literal["tools", "__end__"]
Use in the conditional_edge to route to the ToolNode if the last message

has tool calls. Otherwise, route to the end.

Parameters:

Name	Type	Description	Default
state	Union[list[AnyMessage], dict[str, Any], BaseModel]	The state to check for tool calls. Must have a list of messages or have the "messages" key (StateGraph).	required
Returns:

Type	Description
Literal['tools', '__end__']	The next node to route to.
Examples:

Create a custom ReAct-style agent with tools.


>>> from langchain_anthropic import ChatAnthropic
>>> from langchain_core.tools import tool
...
>>> from langgraph.graph import StateGraph
>>> from langgraph.prebuilt import ToolNode, tools_condition
>>> from langgraph.graph.message import add_messages
...
>>> from typing import Annotated
>>> from typing_extensions import TypedDict
...
>>> @tool
>>> def divide(a: float, b: float) -> int:
...     """Return a / b."""
...     return a / b
...
>>> llm = ChatAnthropic(model="claude-3-haiku-20240307")
>>> tools = [divide]
...
>>> class State(TypedDict):
...     messages: Annotated[list, add_messages]
>>>
>>> graph_builder = StateGraph(State)
>>> graph_builder.add_node("tools", ToolNode(tools))
>>> graph_builder.add_node("chatbot", lambda state: {"messages":llm.bind_tools(tools).invoke(state['messages'])})
>>> graph_builder.add_edge("tools", "chatbot")
>>> graph_builder.add_conditional_edges(
...     "chatbot", tools_condition
... )
>>> graph_builder.set_entry_point("chatbot")
>>> graph = graph_builder.compile()
>>> graph.invoke({"messages": {"role": "user", "content": "What's 329993 divided by 13662?"}})
 ValidationNode ¶
Bases: RunnableCallable

A node that validates all tools requests from the last AIMessage.

It can be used in StateGraph with a "messages" key.

Note

This node does not actually run the tools, it only validates the tool calls, which is useful for extraction and other use cases where you need to generate structured output that conforms to a complex schema without losing the original messages and tool IDs (for use in multi-turn conversations).

Parameters:

Name	Type	Description	Default
schemas	Sequence[Union[BaseTool, Type[BaseModel], Callable]]	A list of schemas to validate the tool calls with. These can be any of the following: - A pydantic BaseModel class - A BaseTool instance (the args_schema will be used) - A function (a schema will be created from the function signature)	required
format_error	Optional[Callable[[BaseException, ToolCall, Type[BaseModel]], str]]	A function that takes an exception, a ToolCall, and a schema and returns a formatted error string. By default, it returns the exception repr and a message to respond after fixing validation errors.	None
name	str	The name of the node.	'validation'
tags	Optional[list[str]]	A list of tags to add to the node.	None
Returns:

Type	Description
Union[Dict[str, List[ToolMessage]], Sequence[ToolMessage]]	A list of ToolMessages with the validated content or error messages.
Example
Example usage for re-prompting the model to generate a valid response:

from typing import Literal, Annotated
from typing_extensions import TypedDict

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, field_validator

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ValidationNode
from langgraph.graph.message import add_messages

class SelectNumber(BaseModel):
    a: int

    @field_validator("a")
    def a_must_be_meaningful(cls, v):
        if v != 37:
            raise ValueError("Only 37 is allowed")
        return v

builder = StateGraph(Annotated[list, add_messages])
llm = ChatAnthropic(model="claude-3-5-haiku-latest").bind_tools([SelectNumber])
builder.add_node("model", llm)
builder.add_node("validation", ValidationNode([SelectNumber]))
builder.add_edge(START, "model")

def should_validate(state: list) -> Literal["validation", "__end__"]:
    if state[-1].tool_calls:
        return "validation"
    return END

builder.add_conditional_edges("model", should_validate)

def should_reprompt(state: list) -> Literal["model", "__end__"]:
    for msg in state[::-1]:
        # None of the tool calls were errors
        if msg.type == "ai":
            return END
        if msg.additional_kwargs.get("is_error"):
            return "model"
    return END

builder.add_conditional_edges("validation", should_reprompt)

graph = builder.compile()
res = graph.invoke(("user", "Select a number, any number"))
# Show the retry logic
for msg in res:
    msg.pretty_print()
Classes:

Name	Description
HumanInterruptConfig	Configuration that defines what actions are allowed for a human interrupt.
ActionRequest	Represents a request for human action within the graph execution.
HumanInterrupt	Represents an interrupt triggered by the graph that requires human intervention.
HumanResponse	The response provided by a human to an interrupt, which is returned when graph execution resumes.
 HumanInterruptConfig ¶
Bases: TypedDict

Configuration that defines what actions are allowed for a human interrupt.

This controls the available interaction options when the graph is paused for human input.

Attributes:

Name	Type	Description
allow_ignore	bool	Whether the human can choose to ignore/skip the current step
allow_respond	bool	Whether the human can provide a text response/feedback
allow_edit	bool	Whether the human can edit the provided content/state
allow_accept	bool	Whether the human can accept/approve the current state
 ActionRequest ¶
Bases: TypedDict

Represents a request for human action within the graph execution.

Contains the action type and any associated arguments needed for the action.

Attributes:

Name	Type	Description
action	str	The type or name of action being requested (e.g., "Approve XYZ action")
args	dict	Key-value pairs of arguments needed for the action
 HumanInterrupt ¶
Bases: TypedDict

Represents an interrupt triggered by the graph that requires human intervention.

This is passed to the interrupt function when execution is paused for human input.

Attributes:

Name	Type	Description
action_request	ActionRequest	The specific action being requested from the human
config	HumanInterruptConfig	Configuration defining what actions are allowed
description	Optional[str]	Optional detailed description of what input is needed
Example

# Extract a tool call from the state and create an interrupt request
request = HumanInterrupt(
    action_request=ActionRequest(
        action="run_command",  # The action being requested
        args={"command": "ls", "args": ["-l"]}  # Arguments for the action
    ),
    config=HumanInterruptConfig(
        allow_ignore=True,    # Allow skipping this step
        allow_respond=True,   # Allow text feedback
        allow_edit=False,     # Don't allow editing
        allow_accept=True     # Allow direct acceptance
    ),
    description="Please review the command before execution"
)
# Send the interrupt request and get the response
response = interrupt([request])[0]
 HumanResponse ¶
Bases: TypedDict

The response provided by a human to an interrupt, which is returned when graph execution resumes.

Attributes:

Name	Type	Description
type	Literal['accept', 'ignore', 'response', 'edit']	The type of response: - "accept": Approves the current state without changes - "ignore": Skips/ignores the current step - "response": Provides text feedback or instructions - "edit": Modifies the current state/content
arg	Literal['accept', 'ignore', 'response', 'edit']	The response payload: - None: For ignore/accept actions - str: For text responses - ActionRequest: For edit actions with updated content


Google Serper
This notebook goes over how to use the Google Serper component to search the web. First you need to sign up for a free account at serper.dev and get your api key.

%pip install --upgrade --quiet  langchain-community langchain-openai

import os
import pprint

os.environ["SERPER_API_KEY"] = "your-serper-api-key"

from langchain_community.utilities import GoogleSerperAPIWrapper

search = GoogleSerperAPIWrapper()

API Reference:GoogleSerperAPIWrapper
search.run("Obama's first name?")

'Barack Hussein Obama II'

As part of a Self Ask With Search Agent
In order to create an agent that uses the Google Serper tool install Langgraph

%pip install --upgrade --quiet langgraph langchain-openai

and use the create_react_agent functionality to initialize a ReAct agent. You will also need to set up your OPEN_API_KEY (visit https://platform.openai.com) in order to access OpenAI's chat models.

from langchain.chat_models import init_chat_model
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent

os.environ["OPENAI_API_KEY"] = "[your openai key]"

llm = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0)
search = GoogleSerperAPIWrapper()
tools = [
    Tool(
        name="Intermediate_Answer",
        func=search.run,
        description="useful for when you need to ask with search",
    )
]
agent = create_react_agent(llm, tools)

events = agent.stream(
    {
        "messages": [
            ("user", "What is the hometown of the reigning men's U.S. Open champion?")
        ]
    },
    stream_mode="values",
)

for event in events:
    event["messages"][-1].pretty_print()

API Reference:init_chat_model | GoogleSerperAPIWrapper | Tool | create_react_agent
Obtaining results with metadata
If you would also like to obtain the results in a structured way including metadata. For this we will be using the results method of the wrapper.

search = GoogleSerperAPIWrapper()
results = search.results("Apple Inc.")
pprint.pp(results)

{'searchParameters': {'q': 'Apple Inc.',
                      'gl': 'us',
                      'hl': 'en',
                      'type': 'search',
                      'num': 10,
                      'engine': 'google'},
 'knowledgeGraph': {'title': 'Apple',
                    'type': 'Technology company',
                    'website': 'http://www.apple.com/',
                    'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT5ITHsQzdzkkFWKinRe1Y4FUbC_Vy3R_M&s=0',
                    'description': 'Apple Inc. is an American multinational '
                                   'corporation and technology company '
                                   'headquartered in Cupertino, California, in '
                                   'Silicon Valley. It is best known for its '
                                   'consumer electronics, software, and '
                                   'services.',
                    'descriptionSource': 'Wikipedia',
                    'descriptionLink': 'https://en.wikipedia.org/wiki/Apple_Inc.',
                    'attributes': {'Customer service': '1 (800) 275-2273',
                                   'Founders': 'Steve Jobs, Steve Wozniak, and '
                                               'Ronald Wayne',
                                   'Founded': 'April 1, 1976, Los Altos, CA',
                                   'Headquarters': 'Cupertino, CA',
                                   'CEO': 'Tim Cook (Aug 24, 2011–)'}},
 'organic': [{'title': 'Apple',
              'link': 'https://www.apple.com/',
              'snippet': 'Discover the innovative world of Apple and shop '
                         'everything iPhone, iPad, Apple Watch, Mac, and Apple '
                         'TV, plus explore accessories, entertainment, ...',
              'sitelinks': [{'title': 'Career Opportunities',
                             'link': 'https://www.apple.com/careers/us/'},
                            {'title': 'Support',
                             'link': 'https://support.apple.com/'},
                            {'title': 'Investor Relations',
                             'link': 'https://investor.apple.com/investor-relations/default.aspx'},
                            {'title': 'Apple Leadership',
                             'link': 'https://www.apple.com/leadership/'},
                            {'title': 'Store',
                             'link': 'https://www.apple.com/store'}],
              'position': 1},
             {'title': 'Apple Inc. - Wikipedia',
              'link': 'https://en.wikipedia.org/wiki/Apple_Inc.',
              'snippet': 'Apple Inc. is an American multinational corporation '
                         'and technology company headquartered in Cupertino, '
                         'California, in Silicon Valley. It is best known for '
                         '...',
              'position': 2},
             {'title': 'Apple Inc. (AAPL) Stock Price Today - WSJ',
              'link': 'https://www.wsj.com/market-data/quotes/AAPL',
              'snippet': 'Apple Inc. engages in the design, manufacture, and '
                         'sale of smartphones, personal computers, tablets, '
                         'wearables and accessories, and other varieties of '
                         'related ...',
              'position': 3},
             {'title': 'Apple Inc. | History, Products, Headquarters, & Facts '
                       '- Britannica',
              'link': 'https://www.britannica.com/money/Apple-Inc',
              'snippet': 'American manufacturer of personal computers, '
                         'smartphones, and tablet computers. Apple was the '
                         'first successful personal computer company and ...',
              'date': '5 days ago',
              'position': 4},
             {'title': 'Apple Inc. (AAPL) Company Profile & Facts - Yahoo '
                       'Finance',
              'link': 'https://finance.yahoo.com/quote/AAPL/profile/',
              'snippet': 'See the company profile for Apple Inc. (AAPL) '
                         'including business summary, industry/sector '
                         'information, number of employees, business summary, '
                         '...',
              'position': 5},
             {'title': 'AAPL: Apple Inc Stock Price Quote - NASDAQ GS - '
                       'Bloomberg',
              'link': 'https://www.bloomberg.com/quote/AAPL:US',
              'snippet': 'Apple Inc. designs, manufactures, and markets '
                         'smartphones, personal computers, tablets, wearables '
                         'and accessories, and sells a variety of related '
                         'accessories.',
              'position': 6}],
 'images': [{'title': 'Apple Inc. - Wikipedia',
             'imageUrl': 'https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg',
             'link': 'https://en.wikipedia.org/wiki/Apple_Inc.'},
            {'title': 'Apple Inc. - Wikipedia',
             'imageUrl': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Aerial_view_of_Apple_Park_dllu.jpg/330px-Aerial_view_of_Apple_Park_dllu.jpg',
             'link': 'https://en.wikipedia.org/wiki/Apple_Inc.'},
            {'title': 'Apple',
             'imageUrl': 'https://www.apple.com/ac/structured-data/images/open_graph_logo.png?202110180743',
             'link': 'https://www.apple.com/'},
            {'title': 'Apple Store - Find a Store - Apple',
             'imageUrl': 'https://rtlimages.apple.com/cmc/dieter/store/16_9/R289.png?resize=672:378&output-format=jpg&output-quality=85&interpolation=progressive-bicubic',
             'link': 'https://www.apple.com/retail/'},
            {'title': 'Apple | LinkedIn',
             'imageUrl': 'https://media.licdn.com/dms/image/v2/C560BAQHdAaarsO-eyA/company-logo_200_200/company-logo_200_200/0/1630637844948/apple_logo?e=2147483647&v=beta&t=pOXzU29XHyAnHt2zp2JryxZvMBdKpqxkkbDWtZ_pnEk',
             'link': 'https://www.linkedin.com/company/apple'},
            {'title': 'The Founding of Apple Computer, Inc. - This Month in '
                      'Business ...',
             'imageUrl': 'https://tile.loc.gov/storage-services/service/pnp/highsm/49100/49193r.jpg',
             'link': 'https://guides.loc.gov/this-month-in-business-history/april/apple-computer-founded'},
            {'title': 'Apple Inc. (AAPL) Stock Price, News, Quote & History - '
                      'Yahoo Finance',
             'imageUrl': 'https://s.yimg.com/uu/api/res/1.2/wsqdHHH05iioDnVbAb2WPQ--~B/aD01NzY7dz0xMDI0O2FwcGlkPXl0YWNoeW9u/https://media.zenfs.com/en/Benzinga/8f4e6ec4860c044f97cc63cfdd74b4f2.cf.webp',
             'link': 'https://finance.yahoo.com/quote/AAPL/'},
            {'title': 'Apple Store - Find a Store - Apple',
             'imageUrl': 'https://rtlimages.apple.com/cmc/dieter/store/16_9/R219.png?resize=672:378&output-format=jpg&output-quality=85&interpolation=progressive-bicubic',
             'link': 'https://www.apple.com/retail/'},
            {'title': 'Apple Store - Find a Store - Apple',
             'imageUrl': 'https://rtlimages.apple.com/cmc/dieter/store/16_9/R420.png?resize=672:378&output-format=jpg&output-quality=85&interpolation=progressive-bicubic',
             'link': 'https://www.apple.com/retail/'}],
 'peopleAlsoAsk': [{'question': 'What is the Apple Inc?',
                    'snippet': 'It is best known for its consumer electronics, '
                               'software, and services. Founded in 1976 as '
                               'Apple Computer Company by Steve Jobs, Steve '
                               'Wozniak and Ronald Wayne, the company was '
                               'incorporated by Jobs and Wozniak as Apple '
                               'Computer, Inc. the following year. It was '
                               'renamed Apple Inc.',
                    'title': 'Apple Inc. - Wikipedia',
                    'link': 'https://en.wikipedia.org/wiki/Apple_Inc.'},
                   {'question': 'Is Apple an LLC or Inc.?',
                    'snippet': 'Apple Inc., located at One Apple Park Way, '
                               'Cupertino, California, for users in the United '
                               'States, including Puerto Rico.',
                    'title': 'Legal - Privacy Policy Affiliated Company - '
                             'Apple',
                    'link': 'https://www.apple.com/legal/privacy/en-ww/affiliated-company/'}],
 'relatedSearches': [{'query': 'apple inc คืออะไร'},
                     {'query': 'Apple Inc full form'},
                     {'query': 'Apple Inc address'},
                     {'query': 'Apple Inc investor relations'},
                     {'query': 'Apple Inc industry'},
                     {'query': 'Apple Inc careers'},
                     {'query': 'Apple Inc Net worth'}],
 'credits': 1}


Searching for Google Images
We can also query Google Images using this wrapper. For example:

search = GoogleSerperAPIWrapper(type="images")
results = search.results("Lion")
pprint.pp(results)

{'searchParameters': {'q': 'Lion',
                      'gl': 'us',
                      'hl': 'en',
                      'type': 'images',
                      'num': 10,
                      'engine': 'google'},
 'images': [{'title': 'Lion - Wikipedia',
             'imageUrl': 'https://upload.wikimedia.org/wikipedia/commons/a/a6/020_The_lion_king_Snyggve_in_the_Serengeti_National_Park_Photo_by_Giles_Laurent.jpg',
             'imageWidth': 5168,
             'imageHeight': 3448,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_HGdbfaRDdKJpWDDdD0AkS58dHashCEbqH9yTMz4j7lQIC6iD&s',
             'thumbnailWidth': 275,
             'thumbnailHeight': 183,
             'source': 'Wikipedia',
             'domain': 'en.wikipedia.org',
             'link': 'https://en.wikipedia.org/wiki/Lion',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fupload.wikimedia.org%2Fwikipedia%2Fcommons%2Fa%2Fa6%2F020_The_lion_king_Snyggve_in_the_Serengeti_National_Park_Photo_by_Giles_Laurent.jpg&tbnid=iu_QQ3Z8fGxRvM&imgrefurl=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FLion&docid=0P9ZPIi_HU4dMM&w=5168&h=3448&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcIAigA',
             'position': 1},
            {'title': 'Lion | Characteristics, Habitat, & Facts | Britannica',
             'imageUrl': 'https://cdn.britannica.com/29/150929-050-547070A1/lion-Kenya-Masai-Mara-National-Reserve.jpg',
             'imageWidth': 1600,
             'imageHeight': 1085,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSCqaKY_THr0IBZN8c-2VApnnbuvKmnsWjfrwKoWHFR9w3eN5o&s',
             'thumbnailWidth': 273,
             'thumbnailHeight': 185,
             'source': 'Britannica',
             'domain': 'www.britannica.com',
             'link': 'https://www.britannica.com/animal/lion',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fcdn.britannica.com%2F29%2F150929-050-547070A1%2Flion-Kenya-Masai-Mara-National-Reserve.jpg&tbnid=DBk5Qx3rVV587M&imgrefurl=https%3A%2F%2Fwww.britannica.com%2Fanimal%2Flion&docid=Zp2R2-BbubSvqM&w=1600&h=1085&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcIAygB',
             'position': 2},
            {'title': 'Lion',
             'imageUrl': 'https://i.natgeofe.com/k/1d33938b-3d02-4773-91e3-70b113c3b8c7/lion-male-roar.jpg?wp=1&w=1084.125&h=609',
             'imageWidth': 1083,
             'imageHeight': 609,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQDDPsOQpmuAhyuNY28gdM0msnIfqxIlLi01CudMaojO5w0xmM&s',
             'thumbnailWidth': 300,
             'thumbnailHeight': 168,
             'source': 'National Geographic Kids',
             'domain': 'kids.nationalgeographic.com',
             'link': 'https://kids.nationalgeographic.com/animals/mammals/facts/lion',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fi.natgeofe.com%2Fk%2F1d33938b-3d02-4773-91e3-70b113c3b8c7%2Flion-male-roar.jpg%3Fwp%3D1%26w%3D1084.125%26h%3D609&tbnid=P9Vzzl57Ow4obM&imgrefurl=https%3A%2F%2Fkids.nationalgeographic.com%2Fanimals%2Fmammals%2Ffacts%2Flion&docid=r48PKzcCogU0oM&w=1083&h=609&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcIBCgC',
             'position': 3},
            {'title': 'Lion | Characteristics, Habitat, & Facts | Britannica',
             'imageUrl': 'https://cdn.britannica.com/30/150930-120-D3D93F1E/lion-panthea-leo-Namibia.jpg',
             'imageWidth': 900,
             'imageHeight': 675,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRYxxLBZ8F_59YdYFJu6y8Zfhf64kMNbrD94uNF0gj9Wgtr4B2k&s',
             'thumbnailWidth': 259,
             'thumbnailHeight': 194,
             'source': 'Britannica',
             'domain': 'www.britannica.com',
             'link': 'https://www.britannica.com/animal/lion',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fcdn.britannica.com%2F30%2F150930-120-D3D93F1E%2Flion-panthea-leo-Namibia.jpg&tbnid=gu4-4upZHrFJ5M&imgrefurl=https%3A%2F%2Fwww.britannica.com%2Fanimal%2Flion&docid=Zp2R2-BbubSvqM&w=900&h=675&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcIBSgD',
             'position': 4},
            {'title': '6,800+ Lion Walking Stock Photos, Pictures & '
                      'Royalty-Free Images ...',
             'imageUrl': 'https://media.istockphoto.com/id/877369086/photo/lion-panthera-leo-10-years-old-isolated-on-white.jpg?s=612x612&w=0&k=20&c=J__Jx_BX_FN7iehO965TJtPFYUl0A-bwFgIYaK32R3Y=',
             'imageWidth': 612,
             'imageHeight': 527,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQNXCI7damJui7Vvf6TQi0ixg_kgvbGQcl9L01u4Rx6ZCI7lqyR&s',
             'thumbnailWidth': 242,
             'thumbnailHeight': 208,
             'source': 'iStock',
             'domain': 'www.istockphoto.com',
             'link': 'https://www.istockphoto.com/photos/lion-walking',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fmedia.istockphoto.com%2Fid%2F877369086%2Fphoto%2Flion-panthera-leo-10-years-old-isolated-on-white.jpg%3Fs%3D612x612%26w%3D0%26k%3D20%26c%3DJ__Jx_BX_FN7iehO965TJtPFYUl0A-bwFgIYaK32R3Y%3D&tbnid=UbVNtrUwB3qvSM&imgrefurl=https%3A%2F%2Fwww.istockphoto.com%2Fphotos%2Flion-walking&docid=VUUNuYLgdvat6M&w=612&h=527&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcIBigE',
             'creator': 'GlobalP',
             'credit': 'Getty Images/iStockphoto',
             'position': 5},
            {'title': 'Free Fierce Lion Roaring Image | Download at StockCake',
             'imageUrl': 'https://images.stockcake.com/public/6/d/2/6d2a992e-cf12-460f-a811-c961e124d9a2_large/fierce-lion-roaring-stockcake.jpg',
             'imageWidth': 408,
             'imageHeight': 728,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRDLNUIqFT5oEh7CNtksHhODRWcuCYkwjHI-sLQXaV4rCPbcO8R&s',
             'thumbnailWidth': 168,
             'thumbnailHeight': 300,
             'source': 'StockCake',
             'domain': 'stockcake.com',
             'link': 'https://stockcake.com/i/fierce-lion-roaring_1358116_1064655',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fimages.stockcake.com%2Fpublic%2F6%2Fd%2F2%2F6d2a992e-cf12-460f-a811-c961e124d9a2_large%2Ffierce-lion-roaring-stockcake.jpg&tbnid=14Bc2UcRYg2vRM&imgrefurl=https%3A%2F%2Fstockcake.com%2Fi%2Ffierce-lion-roaring_1358116_1064655&docid=mIUgDyGFaSvxJM&w=408&h=728&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcIBygF',
             'position': 6},
            {'title': 'Lion | Characteristics, Habitat, & Facts | Britannica',
             'imageUrl': 'https://cdn.britannica.com/55/2155-050-604F5A4A/lion.jpg',
             'imageWidth': 754,
             'imageHeight': 752,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS3fnDub1GSojI0hJ-ZGS8Tv-hkNNloXh98DOwXZoZ_nUs3GWSd&s',
             'thumbnailWidth': 225,
             'thumbnailHeight': 224,
             'source': 'Britannica',
             'domain': 'www.britannica.com',
             'link': 'https://www.britannica.com/animal/lion',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fcdn.britannica.com%2F55%2F2155-050-604F5A4A%2Flion.jpg&tbnid=IhlRPXpsi9aDnM&imgrefurl=https%3A%2F%2Fwww.britannica.com%2Fanimal%2Flion&docid=Zp2R2-BbubSvqM&w=754&h=752&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcICCgG',
             'position': 7},
            {'title': "Bringing Nigeria's lion population back from extinction "
                      '- WildAid',
             'imageUrl': 'https://wildaid.org/wp-content/uploads/2022/08/Untitled-design-32-400x335.png',
             'imageWidth': 400,
             'imageHeight': 335,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTnurDJfi5sllJxVxWFjfyU8nvXqxy3ef2dcxUTNBmLND9aVuQ&s',
             'thumbnailWidth': 245,
             'thumbnailHeight': 205,
             'source': '- WildAid',
             'domain': 'wildaid.org',
             'link': 'https://wildaid.org/bringing-nigerias-lion-population-back-from-extinction/',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fwildaid.org%2Fwp-content%2Fuploads%2F2022%2F08%2FUntitled-design-32-400x335.png&tbnid=ri5ErxfeVw-rUM&imgrefurl=https%3A%2F%2Fwildaid.org%2Fbringing-nigerias-lion-population-back-from-extinction%2F&docid=IRE1bqPePPGKUM&w=400&h=335&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcICSgH',
             'position': 8},
            {'title': 'Lion',
             'imageUrl': 'https://images.photowall.com/products/46596/lion-1.jpg?h=699&q=85',
             'imageWidth': 699,
             'imageHeight': 699,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTT-SMMS4_tLzeHGP8iK6q1f6VuAfAGKuwvRcKhfAmt6GEutoRZ&s',
             'thumbnailWidth': 225,
             'thumbnailHeight': 225,
             'source': 'Photowall',
             'domain': 'www.photowall.com',
             'link': 'https://www.photowall.com/us/lion-1-poster',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Fimages.photowall.com%2Fproducts%2F46596%2Flion-1.jpg%3Fh%3D699%26q%3D85&tbnid=Hx0R3srHGe7c6M&imgrefurl=https%3A%2F%2Fwww.photowall.com%2Fus%2Flion-1-poster&docid=svxN-CF1BznYSM&w=699&h=699&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcICigI',
             'position': 9},
            {'title': 'Lion | Species | WWF',
             'imageUrl': 'https://files.worldwildlife.org/wwfcmsprod/images/Lion_Kenya/story_full_width/92n0a30duq_Medium_WW2116702.jpg',
             'imageWidth': 1000,
             'imageHeight': 600,
             'thumbnailUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQcAAjEbm00R6g4382D54syoBUFN19j80OBd31FAOMwK_S2Pa9d&s',
             'thumbnailWidth': 290,
             'thumbnailHeight': 174,
             'source': 'World Wildlife Fund',
             'domain': 'www.worldwildlife.org',
             'link': 'https://www.worldwildlife.org/species/lion--19',
             'googleUrl': 'https://www.google.com/imgres?imgurl=https%3A%2F%2Ffiles.worldwildlife.org%2Fwwfcmsprod%2Fimages%2FLion_Kenya%2Fstory_full_width%2F92n0a30duq_Medium_WW2116702.jpg&tbnid=N9k7RywguCeZmM&imgrefurl=https%3A%2F%2Fwww.worldwildlife.org%2Fspecies%2Flion--19&docid=RqCpf1UYcQDKxM&w=1000&h=600&ved=0ahUKEwjl5-H3hfmMAxUMvokEHY6wD3gQvFcICygJ',
             'copyright': 'Juozas Cernius',
             'creator': 'Juozas Cernius www.CERNIUS.com',
             'position': 10}],
 'credits': 1}


Searching for Google News
We can also query Google News using this wrapper. For example:

search = GoogleSerperAPIWrapper(type="news")
results = search.results("Tesla Inc.")
pprint.pp(results)

{'searchParameters': {'q': 'Tesla Inc.',
                      'gl': 'us',
                      'hl': 'en',
                      'type': 'news',
                      'num': 10,
                      'engine': 'google'},
 'news': [{'title': 'Tesla stock soars after DoT unveils new self-driving car '
                    'rules, set for near-20% weekly rally',
           'link': 'https://finance.yahoo.com/news/tesla-stock-soars-after-dot-unveils-new-self-driving-car-rules-set-for-near-20-weekly-rally-183748972.html',
           'snippet': 'Tesla (TSLA) stock surged as much as 10% on Friday, '
                      'putting shares on track to log a weekly gain north of '
                      '17% with several positive...',
           'date': '2 days ago',
           'source': 'Yahoo Finance',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTgHH9x2YIdRGyo1VpJC8b5sYrW5-UprLRAT3r4LQDYx1lX1DeNlunoU4mc2w&s',
           'position': 1},
          {'title': 'Tesla Refunds Early India Bookings Signaling Entry Is '
                    'Near',
           'link': 'https://www.bloomberg.com/news/articles/2025-04-25/tesla-tsla-refunds-early-india-bookings-signaling-entry-is-near',
           'snippet': "Tesla Inc.'s India office is refunding early bookers of "
                      'its Model 3, according to emails seen by Bloomberg '
                      'News, sparking speculation the...',
           'date': '1 day ago',
           'source': 'Bloomberg.com',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTme3lE48FWOyFuWDM-o3wZISjba30aHdoRluMkt7zqlrYqCKK5qGZnwbJ89g&s',
           'position': 2},
          {'title': 'Musk needs to become a more normal CEO',
           'link': 'https://www.ft.com/content/4d10da88-5a0b-49b5-9b29-77286f1985ec',
           'snippet': 'And Tesla should become a more normal company.',
           'date': '10 hours ago',
           'source': 'Financial Times',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSbfTHj0V4haC2VU_bI6W_ZNegrScrmvbUrnkjvskZBzvpPh7WzBIjir342Gw&s',
           'position': 3},
          {'title': "Tesla: The 'Musk Put' Is In Play (NASDAQ:TSLA)",
           'link': 'https://seekingalpha.com/article/4778551-tesla-musk-put-in-play',
           'snippet': "Tesla: The 'Musk Put' Is In Play. Apr. 27, 2025 6:02 AM "
                      'ETTesla, Inc. (TSLA) Stock, TSLA:CA StockBYDDF, NIO, '
                      'XPEV, GOOG, TSLA, TSLA:CA13 Comments 1 Like.',
           'date': '10 hours ago',
           'source': 'Seeking Alpha',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSumMVfOINSI7Xip8Z-wLXwg4mpTuryAk4RMJDL-tWTW5DAdi1yR2WVIezaVQ&s',
           'position': 4},
          {'title': 'Tesla: US Federal Autonomous Vehicle Regulatory Framework '
                    'Aligns With Our Thesis',
           'link': 'https://www.morningstar.com/stocks/tesla-us-federal-autonomous-vehicle-regulatory-framework-aligns-with-our-thesis',
           'snippet': "Editor's Note: This analysis was originally published "
                      'as a stock note by Morningstar Equity Research. '
                      'Securities In This Article. Tesla Inc.',
           'date': '1 day ago',
           'source': 'Morningstar',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT_C3JjwfGXEpLowp-cmCMpxTvoMQ3nmOrhya0aLsnIEBrQSorBX3OSCb1svg&s',
           'position': 5},
          {'title': "Elon Musk's Wealth Skyrockets By Billions As Tesla Stock "
                    'Rallies After Billionaire CEO Steps Back From DOGE',
           'link': 'https://www.benzinga.com/markets/25/04/44974342/elon-musks-wealth-skyrockets-by-billions-as-tesla-stock-rallies-after-billionaire-ceo-steps-back-from-doge',
           'snippet': 'The net worth of Elon Musk witnessed a staggering '
                      'increase of $7.5 billion on Wednesday as shares of '
                      'Tesla Inc. (NASDAQ: TSLA) experienced a...',
           'date': '3 days ago',
           'source': 'Benzinga',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTok4iKaGss1or69QeOrnUo8ZEprpI5Etbq6kepYjLBPlIjOOhiX8yRYWeIiw&s',
           'position': 6},
          {'title': 'Why Tesla Inc. (TSLA) Soared Last Week',
           'link': 'https://finance.yahoo.com/news/why-tesla-inc-tsla-soared-180528904.html',
           'snippet': 'We recently published a list of Why These 10 Firms '
                      'Recorded Double-Digit Gains Last Week. In this article, '
                      'we are going to take a look at...',
           'date': '1 day ago',
           'source': 'Yahoo Finance',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTkQBI72ZwZ8mNhFQ58DLH4wJMyfpsA67ONuTDvvOfAjop5kTrOVcymDGairw&s',
           'position': 7},
          {'title': 'Tesla Hikes Canadian Prices and Pushes Its Pre-Tariff '
                    'Inventory',
           'link': 'https://www.bloomberg.com/news/articles/2025-04-26/tesla-hikes-canadian-prices-and-pushes-its-pre-tariff-inventory',
           'snippet': 'Tesla Inc. is raising prices in Canada and encouraging '
                      'buyers to snap up cars imported before counter-tariffs '
                      'were imposed on US-made...',
           'date': '1 day ago',
           'source': 'Bloomberg.com',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ3pUCdm4COUa4ckj6l-_oqzQUQyPZ_TwxylDHsKfQ5OHaTeC5C14xi3xTPjw&s',
           'position': 8},
          {'title': 'Tesla, Inc. (TSLA) Faces Weak Q1 Auto Revenues but '
                    'Stresses Long-Term AI and Robotics Vision',
           'link': 'https://finance.yahoo.com/news/tesla-inc-tsla-faces-weak-142059117.html',
           'snippet': 'We recently compiled a list of the 12 AI Stocks '
                      'Analysts Are Talking About Right Now. In this article, '
                      'we are going to take a look at where...',
           'date': '1 day ago',
           'source': 'Yahoo Finance',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAF15LDx0VBN7Yhpe99fDywZVZOe2rC4QAQgOyIXyRMMEbUURh_ujyCqQHQg&s',
           'position': 9},
          {'title': 'Analyst Says Tesla (TSLA) Valuation Still ‘Incredibly '
                    'Rich’ as Chinese Companies ‘Eat’ Its Market Share',
           'link': 'https://finance.yahoo.com/news/analyst-says-tesla-tsla-valuation-183703204.html',
           'snippet': 'We recently published a list of Top 10 Stocks to Watch '
                      'Ahead of May. In this article, we are going to take a '
                      'look at where Tesla, Inc.',
           'date': '2 hours ago',
           'source': 'Yahoo Finance',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTd5uofRE66VcJeA46Ewvop5DmICfn3q1dYjk7QydsDVIp12Qtn4rTtzQJJ4g&s',
           'position': 10}],
 'credits': 1}


If you want to only receive news articles published in the last hour, you can do the following:

search = GoogleSerperAPIWrapper(type="news", tbs="qdr:h")
results = search.results("Tesla Inc.")
pprint.pp(results)

{'searchParameters': {'q': 'Tesla Inc.',
                      'gl': 'us',
                      'hl': 'en',
                      'type': 'news',
                      'num': 10,
                      'tbs': 'qdr:h',
                      'engine': 'google'},
 'news': [{'title': 'Big Tech faces high-stakes earnings week amid tariff '
                    'jitters',
           'link': 'https://seekingalpha.com/news/4436090-big-tech-faces-high-stakes-earnings-week-amid-tariff-jitters',
           'snippet': 'When Big Tech last reported earnings, President Donald '
                      'Trump had just taken office, optimism over a pro-growth '
                      'agenda was fueling a stock rally and...',
           'date': '3 minutes ago',
           'source': 'Seeking Alpha',
           'imageUrl': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ9sc9IB67rgImvp7XEOuMDzLhJ6uj7-kNRp6vCShZ7Z9KzDqAR2OeKyHeKvg&s',
           'position': 1}],
 'credits': 1}


Some examples of the tbs parameter:

qdr:h (past hour) qdr:d (past day) qdr:w (past week) qdr:m (past month) qdr:y (past year)

You can specify intermediate time periods by adding a number: qdr:h12 (past 12 hours) qdr:d3 (past 3 days) qdr:w2 (past 2 weeks) qdr:m6 (past 6 months) qdr:m2 (past 2 years)

For all supported filters simply go to Google Search, search for something, click on "Tools", add your date filter and check the URL for "tbs=".

Searching for Google Places
We can also query Google Places using this wrapper. For example:

search = GoogleSerperAPIWrapper(type="places")
results = search.results("Italian restaurants in Upper East Side")
pprint.pp(results)

{'searchParameters': {'q': 'Italian restaurants in Upper East Side',
                      'gl': 'us',
                      'hl': 'en',
                      'type': 'places',
                      'num': 10,
                      'engine': 'google'},
 'places': [{'position': 1,
             'title': "Tony's Di Napoli",
             'address': '1081 3rd Ave, New York, NY 10065',
             'latitude': 40.7643567,
             'longitude': -73.9642373,
             'rating': 4.6,
             'ratingCount': 2900,
             'priceLevel': '$$',
             'category': 'Italian restaurant',
             'phoneNumber': '(212) 888-6333',
             'website': 'http://www.tonysnyc.com/',
             'cid': '1820798058748048984'},
            {'position': 2,
             'title': "L'Osteria",
             'address': '1219 Lexington Ave, New York, NY 10028',
             'latitude': 40.7771565,
             'longitude': -73.9571345,
             'rating': 4.7,
             'ratingCount': 268,
             'priceLevel': '$30–50',
             'category': 'Italian restaurant',
             'phoneNumber': '(646) 524-6294',
             'website': 'http://www.losterianyc.com/',
             'cid': '13046004590297227899'},
            {'position': 3,
             'title': 'La Pecora Bianca UES',
             'address': '1562 2nd Ave, New York, NY 10028',
             'latitude': 40.7746814,
             'longitude': -73.9538665,
             'rating': 4.8,
             'ratingCount': 1300,
             'priceLevel': '$30–50',
             'category': 'Italian restaurant',
             'phoneNumber': '(212) 300-9840',
             'website': 'https://www.lapecorabianca.com/',
             'cid': '6580713665095712525'},
            {'position': 4,
             'title': 'Masseria East',
             'address': '1404 3rd Ave, New York, NY 10075',
             'latitude': 40.774910000000006,
             'longitude': -73.957163,
             'rating': 4.7,
             'ratingCount': 299,
             'priceLevel': '$30–50',
             'category': 'Italian restaurant',
             'phoneNumber': '(212) 535-3520',
             'website': 'http://www.masseriaeast.com/',
             'cid': '1165555394655432498'},
            {'position': 5,
             'title': 'Pavin 86',
             'address': '1663 1st Ave, New York, NY 10028',
             'latitude': 40.777448,
             'longitude': -73.94927679999999,
             'rating': 5,
             'ratingCount': 11,
             'priceLevel': '$20–30',
             'category': 'Italian restaurant',
             'phoneNumber': '(646) 368-1666',
             'cid': '14616385514965614026'},
            {'position': 6,
             'title': 'Piccola Cucina Uptown',
             'address': '106 E 60th St, New York, NY 10022',
             'latitude': 40.7632756,
             'longitude': -73.96896149999999,
             'rating': 4.6,
             'ratingCount': 1900,
             'priceLevel': '$30–50',
             'category': 'Italian restaurant',
             'phoneNumber': '(646) 707-3997',
             'website': 'https://www.piccolacucinagroup.com/',
             'cid': '12569403914342629464'},
            {'position': 7,
             'title': 'La Voglia NYC',
             'address': '1645 3rd Ave, New York, NY 10128',
             'latitude': 40.782702,
             'longitude': -73.95094569999999,
             'rating': 4.4,
             'ratingCount': 360,
             'priceLevel': '$50–100',
             'category': 'Italian restaurant',
             'phoneNumber': '(212) 417-0181',
             'website': 'http://www.lavoglianyc.com/',
             'cid': '1355377864710486791'},
            {'position': 8,
             'title': 'da Adriano',
             'address': '1198 1st Ave, New York, NY 10065',
             'latitude': 40.7631383,
             'longitude': -73.95919169999999,
             'rating': 4.8,
             'ratingCount': 240,
             'priceLevel': '$30–50',
             'category': 'Italian restaurant',
             'phoneNumber': '(646) 371-9412',
             'website': 'http://daadriano.com/',
             'cid': '988704178780025788'},
            {'position': 9,
             'title': 'L’incontro by Rocco',
             'address': '1572 2nd Ave, New York, NY 10028',
             'latitude': 40.7749695,
             'longitude': -73.95354739999999,
             'rating': 4.7,
             'ratingCount': 1400,
             'priceLevel': '$50–100',
             'category': 'Italian restaurant',
             'phoneNumber': '(718) 721-3532',
             'website': 'https://www.lincontrobyrocco.com/',
             'cid': '7698736469939478155'},
            {'position': 10,
             'title': 'Water & Wheat',
             'address': '1379 3rd Ave, New York, NY 10075',
             'latitude': 40.7738747,
             'longitude': -73.9573571,
             'rating': 4.7,
             'ratingCount': 245,
             'priceLevel': '$30–50',
             'category': 'Italian restaurant',
             'phoneNumber': '(646) 484-5054',
             'website': 'http://www.waterandwheatnyc.com/',
             'cid': '14865033522272348854'}],
 'credits': 1}