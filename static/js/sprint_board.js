/** Drag and Drop logic for Kanban Board — Optimistic UI */
document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    let draggedItem = null;   // the .sprint-task-item wrapper
    let originZone = null;    // the zone the task came from

    function updateColumnCount(zone) {
        const columnBox = zone.closest('.kanban-column-box');
        if (!columnBox) return;
        const count = zone.querySelectorAll('.sprint-task-item').length;
        const badge = columnBox.querySelector('.column-count');
        if (badge) badge.textContent = count;

        // Toggle the empty placeholder
        let placeholder = zone.querySelector('.empty-placeholder');
        if (count === 0) {
            if (!placeholder) {
                placeholder = document.createElement('div');
                placeholder.className = 'text-center text-muted p-4 border border-dashed rounded empty-placeholder';
                placeholder.innerHTML = '<small>No tasks in this status</small>';
                zone.appendChild(placeholder);
            }
        } else {
            if (placeholder) placeholder.remove();
        }
    }

    function bindTaskEvents(taskItem) {
        const card = taskItem.querySelector('.sticky-task-card');
        if (!card || !card.draggable || card.dataset.status === 'completed') return;

        taskItem.addEventListener('dragstart', (e) => {
            draggedItem = taskItem;
            originZone = taskItem.closest('.kanban-tasks-container');
            e.dataTransfer.setData('text/plain', card.dataset.taskId);
            e.dataTransfer.effectAllowed = 'move';
            // Delay adding class so the drag ghost renders cleanly
            requestAnimationFrame(() => card.classList.add('dragging'));
        });

        taskItem.addEventListener('dragend', () => {
            card.classList.remove('dragging');
            draggedItem = null;
            originZone = null;
            document.querySelectorAll('.kanban-tasks-container').forEach(z => z.classList.remove('drag-over'));
        });
    }

    // Bind existing task items
    document.querySelectorAll('.sprint-task-item').forEach(bindTaskEvents);

    // Drop zone logic
    document.querySelectorAll('.kanban-tasks-container').forEach(zone => {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            if (!zone.classList.contains('drag-over')) {
                document.querySelectorAll('.kanban-tasks-container').forEach(z => z.classList.remove('drag-over'));
                zone.classList.add('drag-over');
            }
        });

        zone.addEventListener('dragleave', (e) => {
            // Only remove if actually leaving the zone, not entering a child
            if (!zone.contains(e.relatedTarget)) {
                zone.classList.remove('drag-over');
            }
        });

        zone.addEventListener('drop', async (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');

            if (!draggedItem) return;
            const columnBox = zone.closest('.kanban-column-box');
            if (!columnBox) return;

            const newStatus = columnBox.dataset.status;
            const card = draggedItem.querySelector('.sticky-task-card');
            const taskId = card?.dataset.taskId;
            if (!taskId) return;

            const oldStatus = card.dataset.status;
            if (oldStatus === 'completed') return;
            const storyPoints = Number(card.dataset.storyPoints) || 0;

            // Optimistic UI: move the card immediately
            const placeholder = zone.querySelector('.empty-placeholder');
            if (placeholder) placeholder.remove();
            zone.appendChild(draggedItem);
            updateColumnCount(originZone);
            updateColumnCount(zone);

            // If dropped in the same status column, no status update is needed
            if (oldStatus === newStatus) {
                return;
            }

            // Immediately update card status attribute
            card.dataset.status = newStatus;

            // Instantly update burndown chart (simultaneous optimistic update)
            document.dispatchEvent(new CustomEvent('sprint-task-status-optimistic', {
                detail: {
                    taskId,
                    oldStatus,
                    newStatus,
                    storyPoints,
                },
            }));

            // Save to server in background
            const data = new FormData();
            data.append('status', newStatus);
            try {
                const response = await fetch(`/tasks/${taskId}/sprint-status/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: data,
                });

                if (response.redirected) {
                    window.location.assign(response.url);
                    return;
                }

                const result = await response.json();
                if (!response.ok || !result.ok) {
                    throw new Error(Object.values(result.errors || {}).flat().join(' ') || 'Unable to update task status.');
                }

                if (newStatus === 'completed') {
                    card.removeAttribute('draggable');
                    card.draggable = false;
                }

                // Dispatch event with authoritative burndown from server
                document.dispatchEvent(new CustomEvent('sprint-task-status-changed', {
                    detail: {
                        taskId,
                        newStatus,
                        burndown: result.burndown,
                    },
                }));
            } catch (err) {
                // Rollback: move card back to origin
                card.dataset.status = oldStatus;
                if (originZone) {
                    originZone.appendChild(draggedItem);
                    updateColumnCount(zone);
                    updateColumnCount(originZone);
                }
                alert(err.message || 'Unable to update task status. Please try again.');
                // Re-sync burndown chart in case of rollback
                document.dispatchEvent(new CustomEvent('sprint-task-status-changed'));
            }
        });
    });
});
