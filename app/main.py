import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.agent import create_crm_agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

crm_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global crm_agent
    crm_agent = await create_crm_agent()
    yield


app = FastAPI(title="CRM Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple Q&A chain
llm = ChatOpenAI(model="gpt-4o-mini")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Answer the user's question concisely."),
    ("human", "{question}"),
])
chain = prompt | llm


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    question: str
    answer: str


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    thread_id: str


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AnswerResponse)
async def ask(request: QuestionRequest):
    response = await chain.ainvoke({"question": request.question})
    return AnswerResponse(question=request.question, answer=response.content)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    result = await crm_agent.ainvoke(
        {"messages": [HumanMessage(content=request.message)]},
        config=config,
    )
    # Log tool calls and responses for debugging
    for msg in result["messages"]:
        if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                logger.info(f"[TOOL CALL] {tc['name']}: {json.dumps(tc['args'])[:500]}")
        elif msg.type == "tool":
            logger.info(f"[TOOL RESULT] {str(msg.content)[:300]}")
    ai_message = result["messages"][-1]
    content = ai_message.content
    if isinstance(content, list):
        content = "\n".join(
            block["text"] for block in content if block.get("type") == "text"
        )
    return ChatResponse(response=content, thread_id=request.thread_id)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}

    async def event_generator():
        async for event in crm_agent.astream_events(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_tool_start":
                tool_name = event.get("name", "")
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"

            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = chunk.content
                if not content:
                    continue
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                else:
                    continue
                if text:
                    yield f"data: {json.dumps({'type': 'token', 'token': text})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'thread_id': request.thread_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


app.mount("/static", StaticFiles(directory="static"), name="static")
