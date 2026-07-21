import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web-scraper-agent")

app = FastAPI(title="Web Scraper Agent - Joki Tugas System")

# Whitelist CORS origin as per PDF guide
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jokitugas.bananaunion.web.id"],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# API Contract Models
class Payload(BaseModel):
    url: str
    keyword: Optional[str] = ""
    raw_text: Optional[str] = ""

class Metadata(BaseModel):
    sender: str
    timestamp: int

class ScraperRequest(BaseModel):
    task_id: str
    agent_type: str
    payload: Payload
    metadata: Metadata

class SuccessData(BaseModel):
    result: str
    file_url: Optional[str] = None

class SuccessResponse(BaseModel):
    status: str = "success"
    task_id: str
    data: SuccessData
    message: str = "Pemrosesan berhasil"

class ErrorResponse(BaseModel):
    status: str = "error"
    task_id: str
    data: Optional[Any] = None
    message: str

@app.post("/process", response_model=SuccessResponse)
async def process_task(request: ScraperRequest):
    # Log incoming request
    logger.info(f"Received request for task_id: {request.task_id}")
    
    if request.agent_type != "web_scraper":
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "task_id": request.task_id,
                "data": None,
                "message": f"Agent type mismatch. Expected 'web_scraper', got '{request.agent_type}'"
            }
        )

    target_url = request.payload.url.strip()
    if not target_url:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "task_id": request.task_id,
                "data": None,
                "message": "URL payload cannot be empty."
            }
        )

    try:
        # Fetching target URL using httpx with a timeout
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(target_url, headers=headers)
            response.raise_for_status()
            
        # Parsing HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script, style, and navigation metadata tags
        for element in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
            element.extract()
            
        # Get readable text
        raw_text = soup.get_text(separator="\n")
        
        # Clean up whitespace and empty lines
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)
        
        # Limit character count to avoid blowing up context, but keep it substantial
        if len(cleaned_text) > 50000:
            cleaned_text = cleaned_text[:50000] + "\n\n[Content truncated due to length limits...]"
            
        if not cleaned_text:
            cleaned_text = "No readable text content found on the webpage."

        # Return success response matching the PDF SOP
        return SuccessResponse(
            task_id=request.task_id,
            data=SuccessData(
                result=cleaned_text,
                file_url=None
            )
        )

    except Exception as e:
        logger.error(f"Error while scraping {target_url}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "task_id": request.task_id,
                "data": None,
                "message": f"Error scraping the website: {str(e)}"
            }
        )

# Global custom handlers for HTTP exceptions and other exceptions to guarantee format compatibility
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    if isinstance(exc.detail, dict) and "status" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "task_id": "unknown",
            "data": None,
            "message": str(exc.detail)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "task_id": "unknown",
            "data": None,
            "message": f"Internal Server Error: {str(exc)}"
        }
    )

# Root endpoint for checking health
@app.get("/")
async def root():
    return {"status": "online", "agent_type": "web_scraper", "owner": "fadel"}
