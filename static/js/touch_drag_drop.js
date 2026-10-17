/**
 * AgileFlow Touch Drag & Drop Bridge (Phones & Tablets)
 * Translates Touch gestures into standard HTML5 Drag & Drop events
 * Supports:
 * - Kanban Sprint Board columns (with auto-scroll between swipeable columns)
 * - Product Backlog -> Sprint dropzones
 * - Long-press activation to preserve normal tapping and page scrolling
 * - Visual elevated drag ghost with smooth 60fps tracking
 * - Haptic feedback on supported mobile devices
 */
(function () {
    'use strict';

    // Only activate if touch is supported
    if (!('ontouchstart' in window || navigator.maxTouchPoints > 0)) {
        return;
    }

    class SimulatedDataTransfer {
        constructor() {
            this.dropEffect = 'move';
            this.effectAllowed = 'all';
            this.data = {};
            this.types = [];
        }

        setData(format, data) {
            const key = String(format).toLowerCase();
            this.data[key] = String(data);
            if (!this.types.includes(key)) {
                this.types.push(key);
            }
        }

        getData(format) {
            const key = String(format).toLowerCase();
            return this.data[key] || '';
        }

        clearData(format) {
            if (format) {
                const key = String(format).toLowerCase();
                delete this.data[key];
                this.types = this.types.filter(t => t !== key);
            } else {
                this.data = {};
                this.types = [];
            }
        }

        setDragImage() {
            // Handled via custom visual drag ghost
        }
    }

    let dragStartTimer = null;
    let isDragging = false;
    let dragSource = null;
    let dragGhost = null;
    let dataTransfer = null;
    let touchOffsetX = 0;
    let touchOffsetY = 0;
    let startTouchX = 0;
    let startTouchY = 0;
    let lastTouchX = 0;
    let lastTouchY = 0;
    let currentDropTarget = null;
    let scrollRafId = null;
    let preventNextClick = false;

    const HOLD_DELAY_MS = 180; // Hold time required to initiate drag (allows instant tap & quick scroll)
    const MOVE_THRESHOLD_PX = 8; // Movement threshold before hold cancels drag in favor of scroll

    function findDraggable(target) {
        if (!target || !target.closest) return null;
        const candidate = target.closest('.sticky-task-card, .backlog-task-row, .task-card, [draggable="true"][data-task-id]');
        if (!candidate) return null;

        if (candidate.getAttribute('draggable') === 'false' || candidate.dataset.status === 'completed') {
            return null;
        }

        // If candidate is inside a completed sprint or non-draggable container
        const sprintContainer = candidate.closest('.sprint-backlog-container');
        if (sprintContainer && sprintContainer.dataset.canDrag === 'false') {
            return null;
        }

        return candidate;
    }

    function findDropTarget(elementUnder) {
        if (!elementUnder) return null;

        // Check if inside a Kanban column
        const columnBox = elementUnder.closest('.kanban-column-box');
        if (columnBox) {
            return columnBox.querySelector('.kanban-tasks-container') || columnBox;
        }

        // Check for kanban tasks container directly
        const kanbanZone = elementUnder.closest('.kanban-tasks-container');
        if (kanbanZone) return kanbanZone;

        // Check for backlog dropzone
        const dropzone = elementUnder.closest('.dropzone');
        if (dropzone) return dropzone;

        return null;
    }

    function dispatchDragEvent(type, target, dt, touch, relatedTarget) {
        if (!target) return false;
        let evt;
        try {
            evt = new CustomEvent(type, {
                bubbles: true,
                cancelable: true,
                detail: null
            });
        } catch (e) {
            evt = document.createEvent('CustomEvent');
            evt.initCustomEvent(type, true, true, null);
        }

        evt.dataTransfer = dt;
        evt.clientX = touch.clientX;
        evt.clientY = touch.clientY;
        evt.pageX = touch.pageX || touch.clientX;
        evt.pageY = touch.pageY || touch.clientY;
        evt.screenX = touch.screenX || touch.clientX;
        evt.screenY = touch.screenY || touch.clientY;
        evt.button = 0;
        evt.buttons = 1;
        if (relatedTarget) {
            evt.relatedTarget = relatedTarget;
        }

        return target.dispatchEvent(evt);
    }

    function createDragGhost(source, touch) {
        const rect = source.getBoundingClientRect();
        touchOffsetX = touch.clientX - rect.left;
        touchOffsetY = touch.clientY - rect.top;

        const ghost = source.cloneNode(true);
        ghost.classList.add('touch-drag-ghost');
        ghost.style.position = 'fixed';
        ghost.style.left = '0px';
        ghost.style.top = '0px';
        ghost.style.width = `${rect.width}px`;
        ghost.style.height = `${rect.height}px`;
        ghost.style.margin = '0';
        ghost.style.pointerEvents = 'none';
        ghost.style.boxSizing = 'border-box';
        ghost.style.zIndex = '100000';
        ghost.style.transform = `translate3d(${touch.clientX - touchOffsetX}px, ${touch.clientY - touchOffsetY}px, 0) scale(1.05) rotate(2deg)`;

        document.body.appendChild(ghost);
        return ghost;
    }

    function checkAutoScroll(touchX, touchY) {
        const edgeZone = 60;
        const maxScrollSpeed = 16;
        let deltaX = 0;
        let deltaY = 0;

        const kanbanGrid = document.querySelector('.kanban-columns-grid');

        if (touchX < edgeZone) {
            deltaX = -Math.round(((edgeZone - touchX) / edgeZone) * maxScrollSpeed);
        } else if (touchX > window.innerWidth - edgeZone) {
            deltaX = Math.round(((touchX - (window.innerWidth - edgeZone)) / edgeZone) * maxScrollSpeed);
        }

        if (touchY < edgeZone) {
            deltaY = -Math.round(((edgeZone - touchY) / edgeZone) * maxScrollSpeed);
        } else if (touchY > window.innerHeight - edgeZone) {
            deltaY = Math.round(((touchY - (window.innerHeight - edgeZone)) / edgeZone) * maxScrollSpeed);
        }

        if (deltaX !== 0 || deltaY !== 0) {
            if (!scrollRafId) {
                const scrollStep = () => {
                    if (kanbanGrid && deltaX !== 0) {
                        kanbanGrid.scrollLeft += deltaX;
                    } else if (deltaX !== 0) {
                        window.scrollBy(deltaX, 0);
                    }
                    if (deltaY !== 0) {
                        window.scrollBy(0, deltaY);
                    }
                    if (isDragging && (deltaX !== 0 || deltaY !== 0)) {
                        scrollRafId = requestAnimationFrame(scrollStep);
                    } else {
                        scrollRafId = null;
                    }
                };
                scrollRafId = requestAnimationFrame(scrollStep);
            }
        } else {
            if (scrollRafId) {
                cancelAnimationFrame(scrollRafId);
                scrollRafId = null;
            }
        }
    }

    function stopAutoScroll() {
        if (scrollRafId) {
            cancelAnimationFrame(scrollRafId);
            scrollRafId = null;
        }
    }

    function onTouchStart(e) {
        if (e.touches.length !== 1) {
            cleanupDrag();
            return;
        }

        const touch = e.touches[0];
        const draggable = findDraggable(e.target);
        if (!draggable) return;

        startTouchX = touch.clientX;
        startTouchY = touch.clientY;
        lastTouchX = touch.clientX;
        lastTouchY = touch.clientY;
        dragSource = draggable;

        // Start hold timer
        dragStartTimer = setTimeout(() => {
            initiateDrag(touch);
        }, HOLD_DELAY_MS);
    }

    function initiateDrag(touch) {
        if (!dragSource) return;

        isDragging = true;
        preventNextClick = true;

        if (navigator.vibrate) {
            try { navigator.vibrate(35); } catch (_) {}
        }

        // Disable scroll snapping during drag on Kanban board for smooth auto-scrolling
        const kanbanGrid = document.querySelector('.kanban-columns-grid');
        if (kanbanGrid) {
            kanbanGrid.dataset.prevScrollSnap = kanbanGrid.style.scrollSnapType;
            kanbanGrid.style.scrollSnapType = 'none';
        }

        document.body.classList.add('touch-dragging-active');
        dragSource.classList.add('touch-drag-source', 'is-dragging', 'dragging');

        dataTransfer = new SimulatedDataTransfer();
        if (dragSource.dataset.taskId) {
            dataTransfer.setData('text/plain', dragSource.dataset.taskId);
        }

        dragGhost = createDragGhost(dragSource, touch);

        // Dispatch dragstart on dragSource (bubbles to parent handlers in sprint_board.js & backlog.js)
        dispatchDragEvent('dragstart', dragSource, dataTransfer, touch);
    }

    function onTouchMove(e) {
        if (e.touches.length !== 1) {
            if (isDragging) cleanupDrag();
            return;
        }

        const touch = e.touches[0];
        lastTouchX = touch.clientX;
        lastTouchY = touch.clientY;

        if (!isDragging) {
            if (dragStartTimer) {
                const moveDist = Math.hypot(touch.clientX - startTouchX, touch.clientY - startTouchY);
                if (moveDist > MOVE_THRESHOLD_PX) {
                    clearTimeout(dragStartTimer);
                    dragStartTimer = null;
                    dragSource = null;
                }
            }
            return;
        }

        // Drag is active: prevent browser page scroll
        e.preventDefault();

        // Update ghost position
        if (dragGhost) {
            const posX = touch.clientX - touchOffsetX;
            const posY = touch.clientY - touchOffsetY;
            dragGhost.style.transform = `translate3d(${posX}px, ${posY}px, 0) scale(1.05) rotate(2deg)`;
        }

        // Check edge auto-scroll
        checkAutoScroll(touch.clientX, touch.clientY);

        // Find drop zone under finger
        const elUnder = document.elementFromPoint(touch.clientX, touch.clientY);
        const dropTarget = findDropTarget(elUnder);

        if (dropTarget !== currentDropTarget) {
            if (currentDropTarget) {
                dispatchDragEvent('dragleave', currentDropTarget, dataTransfer, touch, dropTarget);
            }
            if (dropTarget) {
                dispatchDragEvent('dragenter', dropTarget, dataTransfer, touch, currentDropTarget);
            }
            currentDropTarget = dropTarget;
        }

        if (currentDropTarget) {
            dispatchDragEvent('dragover', currentDropTarget, dataTransfer, touch);
        }
    }

    function onTouchEnd(e) {
        if (dragStartTimer) {
            clearTimeout(dragStartTimer);
            dragStartTimer = null;
        }

        if (!isDragging) {
            dragSource = null;
            return;
        }

        e.preventDefault();
        stopAutoScroll();

        const touch = e.changedTouches ? e.changedTouches[0] : { clientX: lastTouchX, clientY: lastTouchY };
        const elUnder = document.elementFromPoint(touch.clientX, touch.clientY);
        const dropTarget = findDropTarget(elUnder);

        if (dropTarget) {
            dispatchDragEvent('drop', dropTarget, dataTransfer, touch);
        }

        if (dragSource) {
            dispatchDragEvent('dragend', dragSource, dataTransfer, touch);
        }

        cleanupDrag();
    }

    function onTouchCancel() {
        if (dragStartTimer) {
            clearTimeout(dragStartTimer);
            dragStartTimer = null;
        }
        if (isDragging) {
            stopAutoScroll();
            if (dragSource) {
                dispatchDragEvent('dragend', dragSource, dataTransfer, { clientX: lastTouchX, clientY: lastTouchY });
            }
            cleanupDrag();
        }
    }

    function cleanupDrag() {
        isDragging = false;
        stopAutoScroll();

        if (dragGhost) {
            dragGhost.remove();
            dragGhost = null;
        }

        if (dragSource) {
            dragSource.classList.remove('touch-drag-source', 'is-dragging', 'dragging');
            dragSource = null;
        }

        document.body.classList.remove('touch-dragging-active');

        // Restore scroll snap on Kanban grid
        const kanbanGrid = document.querySelector('.kanban-columns-grid');
        if (kanbanGrid && kanbanGrid.dataset.prevScrollSnap !== undefined) {
            kanbanGrid.style.scrollSnapType = kanbanGrid.dataset.prevScrollSnap;
            delete kanbanGrid.dataset.prevScrollSnap;
        }

        // Remove active dropzone highlights
        document.querySelectorAll('.kanban-tasks-container, .dropzone').forEach(z => {
            z.classList.remove('drag-over', 'sprint-drop-hover', 'sprint-drop-active', 'sprint-drop-blocked');
        });

        currentDropTarget = null;
        dataTransfer = null;
    }

    // Capture and suppress the click event on links if a drag was just performed
    window.addEventListener('click', function (e) {
        if (preventNextClick) {
            e.preventDefault();
            e.stopPropagation();
            preventNextClick = false;
        }
    }, true);

    // Register touch listeners with passive: false to allow e.preventDefault()
    document.addEventListener('touchstart', onTouchStart, { passive: false });
    document.addEventListener('touchmove', onTouchMove, { passive: false });
    document.addEventListener('touchend', onTouchEnd, { passive: false });
    document.addEventListener('touchcancel', onTouchCancel, { passive: false });
})();
