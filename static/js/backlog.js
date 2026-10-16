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
    const dropzones = manager?.querySelectorAll('.dropzone') || [];

    draggableTasks.forEach((taskEl) => {
        taskEl.addEventListener('dragstart', (e) => {
            draggedTaskId = taskEl.dataset.taskId;
            taskEl.classList.add('is-dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.clearData();
            e.dataTransfer.setData('text/plain', draggedTaskId);

            // Highlight valid drop zones (not completed or cancelled sprints)
            dropzones.forEach((dropzone) => {
                const status = dropzone.dataset.status;
                if (status !== 'completed' && status !== 'stopped' && status !== 'cancelled') {
                    dropzone.classList.add('sprint-drop-active');
                }
            });
        });

        taskEl.addEventListener('dragend', () => {
            taskEl.classList.remove('is-dragging');
            dropzones.forEach((dropzone) => {
                dropzone.classList.remove('sprint-drop-active', 'sprint-drop-hover', 'sprint-drop-blocked');
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
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';

            const status = dropzone.dataset.status;
            if (status === 'completed' || status === 'stopped' || status === 'cancelled') {
                dropzone.classList.add('sprint-drop-blocked');
                dropzone.classList.remove('sprint-drop-hover');
            } else {
                dropzone.classList.add('sprint-drop-hover');
                dropzone.classList.remove('sprint-drop-blocked');
            }
        });

        dropzone.addEventListener('dragleave', (e) => {
            if (!dropzone.contains(e.relatedTarget)) {
                dropzone.classList.remove('sprint-drop-hover', 'sprint-drop-blocked');
            }
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('sprint-drop-hover', 'sprint-drop-active', 'sprint-drop-blocked');

            const sprintId = dropzone.dataset.sprintId || ""; // empty if product backlog
            const sprintStatus = dropzone.dataset.status;

            if (sprintStatus === 'completed' || sprintStatus === 'stopped' || sprintStatus === 'cancelled') {
                const displayStatus = (sprintStatus === 'stopped' || sprintStatus === 'cancelled') ? 'Cancelled' : 'Completed';
                alert(`Tasks cannot be moved into a ${displayStatus} Sprint.`);
                return;
            }

            const taskId = draggedTaskId || e.dataTransfer.getData('text/plain');
            if (!taskId) return;

            performMoveTask(taskId, sprintId, null);
        });
    });

    function performMoveTask(taskId, sprintId, assigneeAction, newAssigneeId = null) {
        const activeCsrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
        const formData = new FormData();
        formData.append('sprint_id', sprintId);
        if (activeCsrfToken) {
            formData.append('csrfmiddlewaretoken', activeCsrfToken);
        }
        if (assigneeAction) {
            formData.append('assignee_action', assigneeAction);
        }
        if (newAssigneeId) {
            formData.append('new_assignee_id', newAssigneeId);
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
                        const step1 = document.getElementById('assigneeDecisionStep1');
                        const step2 = document.getElementById('assigneeDecisionStep2');
                        const footer1 = document.getElementById('assigneeFooterStep1');
                        const footer2 = document.getElementById('assigneeFooterStep2');
                        const titleIcon = document.getElementById('assigneeModalTitleIcon');
                        const titleText = document.getElementById('assigneeModalTitleText');

                        const resetToStep1 = () => {
                            if (step1) step1.classList.remove('d-none');
                            if (step2) step2.classList.add('d-none');
                            if (footer1) footer1.classList.remove('d-none');
                            if (footer2) footer2.classList.add('d-none');
                            if (titleIcon) titleIcon.className = 'bi bi-person-exclamation text-warning me-2';
                            if (titleText) titleText.textContent = 'Assignee Not in Sprint';
                        };
                        resetToStep1();

                        document.getElementById('assigneeModalName').textContent = data.assignee_name;
                        document.getElementById('assigneeModalNamePrompt').textContent = data.assignee_name;
                        document.getElementById('assigneeModalSprint').textContent = data.sprint_name;

                        // Step 2 elements
                        const reassignOldName = document.getElementById('assigneeReassignOldName');
                        if (reassignOldName) reassignOldName.textContent = data.assignee_name;
                        const reassignSprint = document.getElementById('assigneeReassignSprint');
                        if (reassignSprint) reassignSprint.textContent = data.sprint_name;

                        // Populate select options
                        const selectEl = document.getElementById('selectNewSprintAssignee');
                        if (selectEl) {
                            selectEl.innerHTML = '<option value="">-- Unassigned (Leave without assignee) --</option>';
                            const members = data.sprint_members || [];
                            const emptyNote = document.getElementById('sprintMembersEmptyNote');
                            if (members.length === 0) {
                                if (emptyNote) emptyNote.classList.remove('d-none');
                            } else {
                                if (emptyNote) emptyNote.classList.add('d-none');
                                members.forEach(m => {
                                    const opt = document.createElement('option');
                                    opt.value = m.id;
                                    opt.textContent = m.name + (m.username && m.username !== m.name ? ` (${m.username})` : '');
                                    selectEl.appendChild(opt);
                                });
                            }
                        }

                        const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
                        const btnAdd = document.getElementById('btnAddAssigneeToSprint');
                        const btnRemove = document.getElementById('btnRemoveAssignee');
                        const btnBack = document.getElementById('btnBackToStep1');
                        const btnConfirm = document.getElementById('btnConfirmNewAssignee');

                        const handleAdd = () => {
                            cleanup();
                            bsModal.hide();
                            performMoveTask(taskId, sprintId, 'add_to_sprint');
                        };

                        const handleRemove = () => {
                            // Show Step 2 to allow choosing a new assignee from the team members in the sprint
                            if (step1) step1.classList.add('d-none');
                            if (step2) step2.classList.remove('d-none');
                            if (footer1) footer1.classList.add('d-none');
                            if (footer2) footer2.classList.remove('d-none');
                            if (titleIcon) titleIcon.className = 'bi bi-person-gear text-primary me-2';
                            if (titleText) titleText.textContent = `Choose Assignee for ${data.sprint_name}`;
                        };

                        const handleBack = () => {
                            resetToStep1();
                        };

                        const handleConfirm = () => {
                            const chosenAssigneeId = selectEl ? selectEl.value : '';
                            cleanup();
                            bsModal.hide();
                            performMoveTask(taskId, sprintId, 'remove_assignee', chosenAssigneeId || null);
                        };

                        const cleanup = () => {
                            if (btnAdd) btnAdd.removeEventListener('click', handleAdd);
                            if (btnRemove) btnRemove.removeEventListener('click', handleRemove);
                            if (btnBack) btnBack.removeEventListener('click', handleBack);
                            if (btnConfirm) btnConfirm.removeEventListener('click', handleConfirm);
                            modalEl.removeEventListener('hidden.bs.modal', resetToStep1);
                        };

                        if (btnAdd) btnAdd.addEventListener('click', handleAdd);
                        if (btnRemove) btnRemove.addEventListener('click', handleRemove);
                        if (btnBack) btnBack.addEventListener('click', handleBack);
                        if (btnConfirm) btnConfirm.addEventListener('click', handleConfirm);
                        modalEl.addEventListener('hidden.bs.modal', resetToStep1);

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
                    const errorMsg = data.errors?.task?.[0] || data.errors?.sprint_id?.[0] || data.errors?.assignee?.[0] || data.errors?.non_field_errors?.[0] || 'Validation error';
                    alert(errorMsg);
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
