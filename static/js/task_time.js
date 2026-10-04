/** US-19: Populate the existing edit modal with the selected real work session. */
document.addEventListener('DOMContentLoaded', () => {
    const editModal = document.getElementById('editTimeModal');
    editModal?.addEventListener('show.bs.modal', (event) => {
        const button = event.relatedTarget;
        if (!button) return; // Server validation errors retain the submitted values.
        const form = editModal.querySelector('form');
        form.action = button.dataset.editUrl;
        for (const [field, attribute] of [
            ['start_date', 'startDate'], ['start_time', 'startTime'],
            ['end_date', 'endDate'], ['end_time', 'endTime'],
        ]) {
            form.elements[field].value = button.dataset[attribute];
        }
        editModal.querySelectorAll('.alert-danger').forEach((alert) => alert.remove());
    });

    const reopen = document.querySelector('[data-open-time-modal]')?.dataset.openTimeModal;
    if (reopen && window.bootstrap) {
        const modal = document.getElementById(reopen);
        if (modal) bootstrap.Modal.getOrCreateInstance(modal).show();
    }

    document.querySelectorAll('.work-session-form').forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (form.dataset.submitting) {
                event.preventDefault();
                return;
            }
            form.dataset.submitting = 'true';
            form.querySelector('[type="submit"]').disabled = true;
        });
    });
});
