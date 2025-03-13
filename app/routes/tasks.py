from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..models import get_db
from ..models.user import User
from ..models.task import Task, TaskStatus, PriorityLevel
from ..schemas.task import (
    Task as TaskSchema, 
    TaskCreate, 
    TaskUpdate,
    TaskStatus as TaskStatusSchema,
    PriorityLevel as PriorityLevelSchema,
    NaturalLanguageTaskRequest
)
from ..services.calendar_api import CalendarService
from ..services.nlp import NLPService
from ..utils.auth import get_current_active_user

router = APIRouter(tags=["tasks"], prefix="/tasks")


@router.post("", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new task."""
    calendar_service = CalendarService(db)
    
    task = calendar_service.create_task(
        user_id=current_user.id,
        task_data=task_data.dict()
    )
    
    return task


@router.post("/parse", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task_from_text(
    request: NaturalLanguageTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new task from natural language text."""
    nlp_service = NLPService()
    calendar_service = CalendarService(db)
    
    # Parse task data from text
    task_data = nlp_service.parse_task(request.text)
    
    # Create task
    task = calendar_service.create_task(
        user_id=current_user.id,
        task_data=task_data
    )
    
    return task


@router.get("", response_model=List[TaskSchema])
async def get_tasks(
    status: Optional[TaskStatusSchema] = None,
    priority: Optional[PriorityLevelSchema] = None,
    due_date_start: Optional[datetime] = None,
    due_date_end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all tasks for current user with optional filters."""
    calendar_service = CalendarService(db)
    
    tasks = calendar_service.get_tasks(
        user_id=current_user.id,
        status=status,
        priority=priority,
        due_date_start=due_date_start,
        due_date_end=due_date_end
    )
    
    return tasks


@router.get("/{task_id}", response_model=TaskSchema)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific task by ID."""
    calendar_service = CalendarService(db)
    
    task = calendar_service.get_task(task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    return task


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a task."""
    calendar_service = CalendarService(db)
    
    updated_task = calendar_service.update_task(
        task_id=task_id,
        user_id=current_user.id,
        task_data=task_data.dict(exclude_unset=True)
    )
    
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found or you don't have permission to update it"
        )
    
    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a task."""
    calendar_service = CalendarService(db)
    
    result = calendar_service.delete_task(task_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found or you don't have permission to delete it"
        )
    
    return None


@router.put("/{task_id}/status", response_model=TaskSchema)
async def update_task_status(
    task_id: int,
    status: TaskStatusSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update task status."""
    calendar_service = CalendarService(db)
    
    updated_task = calendar_service.update_task(
        task_id=task_id,
        user_id=current_user.id,
        task_data={"status": status}
    )
    
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found or you don't have permission to update it"
        )
    
    return updated_task