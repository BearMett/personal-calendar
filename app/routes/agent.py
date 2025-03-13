from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models import get_db
from ..models.user import User
from ..schemas.agent import AgentCommandRequest, AgentCommandResponse
from ..services.agent import AgentService
from ..utils.auth import get_current_active_user

router = APIRouter(tags=["agent"], prefix="/agent")


@router.post("/command", response_model=AgentCommandResponse)
async def process_agent_command(
    request: AgentCommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Process a natural language command for the agent."""
    agent_service = AgentService(db)
    
    result = agent_service.process_command(
        user_id=current_user.id,
        text=request.command
    )
    
    return {"response": result}