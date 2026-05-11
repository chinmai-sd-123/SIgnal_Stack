import pytest

from app.services.worker_queue import TaskStatus, WorkerQueue


def _noop():
    return True


@pytest.mark.unit
def test_worker_queue_accepts_multiple_same_priority_tasks():
    queue = WorkerQueue(num_workers=0, max_queue_size=10)

    first = queue.enqueue(_noop, name="first", priority=5)
    second = queue.enqueue(_noop, name="second", priority=5)

    assert first != second
    assert queue.get_queue_size() == 2
    assert queue.tasks[first].status == TaskStatus.PENDING
    assert queue.tasks[second].status == TaskStatus.PENDING

    queue.stop(wait=False)
