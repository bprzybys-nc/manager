import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from .jira import JiraClient, JiraFormatting

# Initialize the FastAPI app
app = FastAPI()

# Dependency function to get Jira client
def get_jira_client():
    try:
        return JiraClient()
    except KeyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Missing environment variable: {e}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing Jira client: {e}")


class JiraCommentRequest(BaseModel):
    comment: str
    formatting: Optional[JiraFormatting] = None


class JiraCloseRequest(BaseModel):
    comment: Optional[str] = None
    formatting: Optional[JiraFormatting] = None

class JiraDetailsResponse(BaseModel):
    description: Optional[str]
    comments: list[str]


@app.post("/tickets/{ticket_id}/comments")
async def add_jira_comment(ticket_id: str, payload: JiraCommentRequest, jira_client: JiraClient = Depends(get_jira_client)):
    try:
        jira_client.add_comment(ticket_id, payload.comment, payload.formatting)
        return {"message": "Comment added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tickets/{ticket_id}")
async def close_jira_ticket(ticket_id: str, payload: JiraCloseRequest, jira_client: JiraClient = Depends(get_jira_client)):
    try:
        jira_client.close_ticket(ticket_id, payload.comment, payload.formatting)
        return {"message": "Ticket closed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tickets/{ticket_id}", response_model=JiraDetailsResponse)
async def get_jira_details(ticket_id: str, jira_client: JiraClient = Depends(get_jira_client)):
    try:
        details = jira_client.get_ticket_details(ticket_id)
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
