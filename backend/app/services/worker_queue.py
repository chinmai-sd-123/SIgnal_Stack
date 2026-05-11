"""
Worker Queue for Background Tasks.

Implements a simple background task queue for:
- Async evaluation processing
- GitHub repository fetching
- LLM summarization
- Snapshot creation

Uses threading for simplicity. Production could use Celery or RQ.
"""

import threading
import queue
import time
import uuid
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import traceback


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a background task."""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 0  # Higher = more urgent


class WorkerQueue:
    """
    Simple background task queue using threads.
    
    Production alternative: Use Celery with Redis/RabbitMQ
    """
    
    def __init__(self, num_workers: int = 3, max_queue_size: int = 100):
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self.tasks: Dict[str, Task] = {}
        self.workers: List[threading.Thread] = []
        self.running = False
        self.num_workers = num_workers
        self._lock = threading.Lock()
    
    def start(self):
        """Start worker threads."""
        if self.running:
            return
        
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"worker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        print(f"Started {self.num_workers} worker threads")
    
    def stop(self, wait: bool = True, timeout: float = 10.0):
        """Stop worker threads."""
        self.running = False
        
        if wait:
            # Add poison pills to wake up workers
            for _ in self.workers:
                try:
                    self.task_queue.put((999, None), timeout=1)
                except queue.Full:
                    pass
            
            for worker in self.workers:
                worker.join(timeout=timeout)
        
        self.workers.clear()
        print("Worker threads stopped")
    
    def _worker_loop(self):
        """Main worker loop - pulls tasks from queue and executes them."""
        while self.running:
            try:
                # Block with timeout to allow checking running flag
                priority, task = self.task_queue.get(timeout=1)
                
                if task is None:  # Poison pill
                    break
                
                self._execute_task(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
    
    def _execute_task(self, task: Task):
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        try:
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            task.status = TaskStatus.FAILED
        finally:
            task.completed_at = datetime.utcnow()
    
    def enqueue(
        self,
        func: Callable,
        *args,
        name: str = None,
        priority: int = 0,
        **kwargs
    ) -> str:
        """
        Add a task to the queue.
        
        Returns task ID for tracking.
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )
        
        with self._lock:
            self.tasks[task_id] = task
        
        # Priority queue uses (priority, task), lower = first
        # Negate priority so higher number = more urgent
        self.task_queue.put((-priority, task))
        
        return task_id
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "result": task.result if task.status == TaskStatus.COMPLETED else None,
            "error": task.error if task.status == TaskStatus.FAILED else None,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        
        return False
    
    def get_queue_size(self) -> int:
        """Get number of pending tasks."""
        return self.task_queue.qsize()
    
    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent tasks."""
        with self._lock:
            sorted_tasks = sorted(
                self.tasks.values(),
                key=lambda t: t.created_at,
                reverse=True
            )[:limit]
        
        return [self.get_status(t.id) for t in sorted_tasks]
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove completed tasks older than max_age_hours."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self._lock:
            to_remove = [
                task_id for task_id, task in self.tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                and task.completed_at and task.completed_at < cutoff
            ]
            for task_id in to_remove:
                del self.tasks[task_id]
        
        return len(to_remove)


from datetime import timedelta

# Global worker queue instance
worker_queue = WorkerQueue(num_workers=3)


# Task decorator for easy async execution
def background_task(priority: int = 0, name: str = None):
    """
    Decorator to run a function as a background task.
    
    Usage:
        @background_task(priority=5, name="fetch_repo")
        def fetch_repository(repo_url: str):
            ...
        
        # Call returns task_id immediately
        task_id = fetch_repository("https://github.com/...")
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            return worker_queue.enqueue(
                func,
                *args,
                name=name or func.__name__,
                priority=priority,
                **kwargs
            )
        wrapper.__name__ = func.__name__
        wrapper.sync = func  # Access original sync version
        return wrapper
    return decorator


# Start workers when module loads
def init_workers():
    """Initialize worker threads (call from main.py startup)."""
    worker_queue.start()
