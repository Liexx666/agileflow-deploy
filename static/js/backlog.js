/**
 * AgileFlow Backlog Client Interactivity (US15-18)
 * FIT2101 - Project Pulse
 * Handles:
 * - Sort dropdown auto-submit
 * - List <-> Card view toggle
 * - Drag & Drop backlog tasks into Active Sprint in the left sidebar (US-15)
 */

document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

    // 0. Preserve scroll positions of columns
    const leftCol = document.querySelector('.col-lg-6:first-child .overflow-y-auto');
    const rightCol = document.querySelector('.col-lg-6:last-child .overflow-y-auto');

    if (leftCol && rightCol) {
        if (sessionStorage.getItem('leftColScroll')) {
            leftCol.scrollTop = sessionStorage.getItem('leftColScroll');
        }
        if (sessionStorage.getItem('rightColScroll')) {
            rightCol.scrollTop = sessionStorage.getItem('rightColScroll');
        }

        window.addEventListener('beforeunload', () => {
            sessionStorage.setItem('leftColScroll', leftCol.scrollTop);
            sessionStorage.setItem('rightColScroll', rightCol.scrollTop);
        });
    }

    // 1. Sort Dropdown Auto Submit
    const sortDropdown = document.getElementById('sortSelect');
    const filterForm = document.getElementById('filterForm');

    if (sortDropdown && filterForm) {
        sortDropdown.addEventListener('change', () => {
            filterForm.submit();
        });
    }

    // 2. View Toggle Switch (List <-> Card)
    const viewToggle = document.getElementById('viewToggle');
    const labelCard = document.getElementById('viewLabelCard');
    const listViewContainers = document.querySelectorAll('.list-view-container');
    const cardViewContainers = document.querySelectorAll('.card-view-container');

    if (viewToggle) {
        const viewStorageKey = 'agileflow.backlog.view';
        const applyView = (isCardView) => {
            viewToggle.checked = isCardView;
            listViewContainers.forEach(container => container.style.display = isCardView ? 'none' : 'block');
            cardViewContainers.forEach(container => container.style.display = isCardView ? 'block' : 'none');
            if (labelCard) labelCard.classList.toggle('active', isCardView);
        };

        let savedView = 'list';
        try {
            savedView = sessionStorage.getItem(viewStorageKey) || 'list';
        } catch {
            // Storage unavailable
        }
        applyView(savedView === 'card');

        viewToggle.addEventListener('change', () => {
            applyView(viewToggle.checked);
            try {
                sessionStorage.setItem(viewStorageKey, viewToggle.checked ? 'card' : 'list');
            } catch {
                // Storage restrictions
            }
        });
    }

    // 3. Drag & Drop Backlog Tasks (US-15 & US-21)
    let draggedTaskId = null;
    const manager = document.querySelector('[data-backlog-manager]');
    const draggableTasks = manager?.querySelectorAll('[draggable="true"][data-task-id]') || [];
    const dropzones = manager?.querySelectorAll('.dropzone[data-can-drop="true"]') || [];

    draggableTasks.forEach((taskEl) => {
        taskEl.addEventListener('dragstart', (e) => {
            draggedTaskId = taskEl.dataset.taskId;
            taskEl.classList.add('is-dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.clearData();
            e.dataTransfer.setData('text/plain', draggedTaskId);

            // Highlight valid drop zones (not completed or stopped sprints)
            dropzones.forEach((dropzone) => {
                const status = dropzone.dataset.status;
                if (status !== 'completed' && status !== 'stopped') {
                    dropzone.classList.add('sprint-drop-active');
                }
            });
        });

        taskEl.addEventListener('dragend', () => {
            taskEl.classList.remove('is-dragging');
            dropzones.forEach((dropzone) => {
                dropzone.classList.remove('sprint-drop-active', 'sprint-drop-hover');
            });
            draggedTaskId = null;
        });
    });

    dropzones.forEach((dropzone) => {
        dropzone.addEventListener('dragenter', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        });
        dropzone.addEventListener('dragover', (e) => {
            const status = dropzone.dataset.status;
            if (status === 'completed' || status === 'stopped') return; // Cannot drop into completed/stopped sprints

            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            dropzone.classList.add('sprint-drop-hover');
        });

        dropzone.addEventListener('dragleave', (e) => {
            if (!dropzone.contains(e.relatedTarget)) {
                dropzone.classList.remove('sprint-drop-hover');
            }
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('sprint-drop-hover', 'sprint-drop-active');

            const taskId = draggedTaskId || e.dataTransfer.getData('text/plain');
            const sprintId = dropzone.dataset.sprintId || ""; // empty if product backlog
            const sprintStatus = dropzone.dataset.status;

            if (!taskId) return;

            if (sprintStatus === 'completed' || sprintStatus === 'stopped') {
                alert(`Tasks cannot be moved into a ${sprintStatus} Sprint.`);
                return;
            }

            performMoveTask(taskId, sprintId, null);
        });
    });

    function performMoveTask(taskId, sprintId, assigneeAction) {
        const activeCsrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
        const formData = new FormData();
        formData.append('sprint_id', sprintId);
        if (activeCsrfToken) {
            formData.append('csrfmiddlewaretoken', activeCsrfToken);
        }
        if (assigneeAction) {
            formData.append('assignee_action', assigneeAction);
        }

        fetch(`/tasks/${taskId}/move/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': activeCsrfToken,
            },
            body: formData,
        })
            .then(async (res) => {
                const data = await res.json().catch(() => null);
                if (res.ok && data && data.ok) {
                    window.location.reload();
                    return;
                }

                if (data && data.needs_assignee_decision) {
                    const modalEl = document.getElementById('assigneeDecisionModal');
                    if (modalEl) {
                        document.getElementById('assigneeModalName').textContent = data.assignee_name;
                        document.getElementById('assigneeModalNamePrompt').textContent = data.assignee_name;
                        document.getElementById('assigneeModalSprint').textContent = data.sprint_name;

                        const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
                        const btnAdd = document.getElementById('btnAddAssigneeToSprint');
                        const btnRemove = document.getElementById('btnRemoveAssignee');

                        const handleAdd = () => {
                            cleanup();
                            bsModal.hide();
                            performMoveTask(taskId, sprintId, 'add_to_sprint');
                        };

                        const handleRemove = () => {
                            cleanup();
                            bsModal.hide();
                            performMoveTask(taskId, sprintId, 'remove_assignee');
                        };

                        const cleanup = () => {
                            btnAdd.removeEventListener('click', handleAdd);
                            btnRemove.removeEventListener('click', handleRemove);
                        };

                        btnAdd.addEventListener('click', handleAdd);
                        btnRemove.addEventListener('click', handleRemove);

                        bsModal.show();
                    } else {
                        if (confirm(`${data.assignee_name} is not in ${data.sprint_name}.\n\nClick OK to add them to the sprint, or Cancel to remove the assignee from the task.`)) {
                            performMoveTask(taskId, sprintId, 'add_to_sprint');
                        } else {
                            performMoveTask(taskId, sprintId, 'remove_assignee');
                        }
                    }
                    return;
                }

                if (data && data.errors) {
                    const errorMsg = data.errors?.task?.[0] || data.errors?.sprint_id?.[0] || data.errors?.non_field_errors?.[0] || 'Validation error';
                    alert('Could not move task: ' + errorMsg);
                } else if (res.status === 403) {
                    alert('Permission denied or CSRF token expired. Please refresh the page.');
                } else {
                    alert('Could not move task. Please refresh the page.');
                }
            })
            .catch((err) => {
                console.error('Move task request failed:', err);
                alert('Network error moving task.');
            });
    }

    // 4. Sprint Status Dropdown Handler (US-18)
    document.querySelectorAll('.sprint-status-option').forEach((optionBtn) => {
        optionBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const sprintId = optionBtn.dataset.sprintId;
            const newStatus = optionBtn.dataset.status;
            const sprintCard = optionBtn.closest('.sprint-item-card');
            const dropdownBtn = sprintCard?.querySelector('.sprint-status-btn');

            if (!sprintId || !newStatus || !dropdownBtn) return;

            const currentStatus = sprintCard.dataset.status;
            if (currentStatus === newStatus) return;

            const formData = new FormData();
            formData.append('status', newStatus);

            fetch(`/sprints/${sprintId}/status/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData,
            })
                .then(async (res) => {
                    const data = await res.json();
                    if (!res.ok || !data.ok) {
                        const errorMsg = data.errors?.status?.[0] || data.errors?.non_field_errors?.[0] || 'Unable to update sprint status.';
                        alert(errorMsg);
                        return;
                    }

                    // Reload page so sprint list and active sprint constraints update cleanly
                    window.location.reload();
                })
                .catch((err) => {
                    console.error('Sprint status update error:', err);
                    alert('Network error updating sprint status.');
                });
        });
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + '=') {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
