/**
 * AgileFlow Backlog Client Interactivity
 * FIT2101 - Project Pulse
 */

document.addEventListener('DOMContentLoaded', () => {
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
    const listViewContainer = document.getElementById('listViewContainer');
    const cardViewContainer = document.getElementById('cardViewContainer');

    if (viewToggle && listViewContainer && cardViewContainer) {
        const viewStorageKey = 'agileflow.backlog.view';
        const applyView = (isCardView) => {
            viewToggle.checked = isCardView;
            listViewContainer.style.display = isCardView ? 'none' : 'block';
            cardViewContainer.style.display = isCardView ? 'block' : 'none';
            if (labelCard) labelCard.classList.toggle('active', isCardView);
        };

        // Restore the choice after sorting, filtering, or returning from a task.
        let savedView = 'list';
        try {
            savedView = sessionStorage.getItem(viewStorageKey) || 'list';
        } catch {
            // The toggle still works when browser storage is unavailable.
        }
        applyView(savedView === 'card');

        viewToggle.addEventListener('change', () => {
            applyView(viewToggle.checked);
            try {
                sessionStorage.setItem(viewStorageKey, viewToggle.checked ? 'card' : 'list');
            } catch {
                // Storage restrictions must not prevent switching views.
            }
        });
    }
});
