from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.logging import logger
from app.models.models import Task, TaskPriority, TaskStatus, User
from app.schemas.schemas import (
    MessageResponse, TaskCreate, TaskListResponse, TaskOut, TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


@router.post(
    "/",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(**payload.model_dump(), owner_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info("task_created", task_id=task.id, user_id=current_user.id)
    return task


@router.get("/", response_model=TaskListResponse, summary="List tasks (paginated)")
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import UserRole
    q = db.query(Task).filter(Task.is_deleted == False)

    # Admins see all tasks; regular users see only their own
    if current_user.role != UserRole.admin:
        q = q.filter(Task.owner_id == current_user.id)

    if status:
        q = q.filter(Task.status == status)
    if priority:
        q = q.filter(Task.priority == priority)

    total = q.count()
    tasks = q.offset((page - 1) * page_size).limit(page_size).all()
    return TaskListResponse(tasks=tasks, total=total, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=TaskOut, summary="Get a single task")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import UserRole
    task = _get_task_or_404(task_id, db)
    if current_user.role != UserRole.admin and task.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your task")
    return task


@router.patch("/{task_id}", response_model=TaskOut, summary="Partially update a task")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import UserRole
    task = _get_task_or_404(task_id, db)
    if current_user.role != UserRole.admin and task.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your task")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    logger.info("task_updated", task_id=task.id, user_id=current_user.id)
    return task


@router.delete(
    "/{task_id}",
    response_model=MessageResponse,
    summary="Soft-delete a task",
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import UserRole
    task = _get_task_or_404(task_id, db)
    if current_user.role != UserRole.admin and task.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your task")

    task.is_deleted = True
    db.commit()
    logger.info("task_deleted", task_id=task.id, user_id=current_user.id)
    return MessageResponse(message="Task deleted")


# ── Admin-only endpoints ──────────────────────────────────────────────────────

@router.get(
    "/admin/all",
    response_model=TaskListResponse,
    summary="[Admin] List ALL tasks across all users",
)
def admin_list_all_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(Task).filter(Task.is_deleted == False)
    total = q.count()
    tasks = q.offset((page - 1) * page_size).limit(page_size).all()
    return TaskListResponse(tasks=tasks, total=total, page=page, page_size=page_size)
