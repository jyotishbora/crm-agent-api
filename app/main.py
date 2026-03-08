from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

app = FastAPI(title="CRM Agent API")

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


@app.get("/")
async def root():
    return {"message": "CRM Agent API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AnswerResponse)
async def ask(request: QuestionRequest):
    response = await chain.ainvoke({"question": request.question})
    return AnswerResponse(question=request.question, answer=response.content)
