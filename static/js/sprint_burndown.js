/** US-21: Draw backend progress data and refresh after successful task changes. */
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('burndownChart');
    const initialData = document.getElementById('sprintBurndownData');
    if (!canvas || !initialData) return;

    const plot = document.getElementById('burndownPlot');
    const summary = document.getElementById('burndownSummary');
    const note = document.getElementById('burndownNote');
    const error = document.getElementById('burndownError');
    let chart = null;
    let latestRequest = 0;
    let currentData = null;

    function showError(message) {
        error.textContent = message;
        error.hidden = false;
    }

    function render(data) {
        if (!data) return;
        currentData = JSON.parse(JSON.stringify(data));
        summary.textContent = `Remaining: ${data.remaining_story_points} / ${data.total_story_points} story points (${data.remaining_percentage}%)`;
        note.textContent = data.note;
        error.hidden = true;
        plot.hidden = !data.available;
        if (!data.available) {
            if (chart) chart.destroy();
            chart = null;
            return;
        }
        if (typeof Chart === 'undefined') {
            plot.hidden = true;
            showError('The chart could not load. Check your connection and reload the page.');
            return;
        }
        if (chart) {
            chart.data.labels = data.labels;
            chart.data.datasets[0].data = data.ideal;
            chart.data.datasets[1].data = data.actual;
            chart.update();
            return;
        }
        chart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    { label: 'Ideal progress', data: data.ideal, borderColor: '#9ca3af', backgroundColor: '#9ca3af', borderDash: [5, 5], pointRadius: 0, borderWidth: 2, tension: 0 },
                    { label: 'Actual progress', data: data.actual, borderColor: '#2563eb', backgroundColor: '#2563eb', pointRadius: 4, borderWidth: 2, tension: 0, spanGaps: false },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', align: 'end' },
                    tooltip: { mode: 'index', intersect: false, callbacks: { label: (context) => `${context.dataset.label}: ${context.parsed.y}%` } },
                },
                scales: {
                    x: { title: { display: true, text: 'Sprint date' } },
                    y: { title: { display: true, text: 'Remaining work (%)' }, min: 0, max: 100, ticks: { stepSize: 20, callback: (value) => `${value}%` } },
                },
            },
        });
    }

    function handleOptimisticChange(e) {
        if (!currentData || !currentData.available) return;
        const detail = e.detail || {};
        const oldStatus = detail.oldStatus;
        const newStatus = detail.newStatus;
        const storyPoints = Number(detail.storyPoints) || 0;
        if (oldStatus === newStatus || storyPoints <= 0) return;

        let delta = 0;
        if (oldStatus !== 'completed' && newStatus === 'completed') {
            delta = -storyPoints;
        } else if (oldStatus === 'completed' && newStatus !== 'completed') {
            delta = storyPoints;
        }

        if (delta === 0) return;

        const newRemaining = Math.max(0, (currentData.remaining_story_points || 0) + delta);
        const total = currentData.total_story_points || 0;
        const newPercentage = total > 0 ? Math.round((newRemaining / total) * 10000) / 100 : 0;

        currentData.remaining_story_points = newRemaining;
        currentData.remaining_percentage = newPercentage;

        if (Array.isArray(currentData.actual)) {
            let targetIdx = -1;
            for (let i = currentData.actual.length - 1; i >= 0; i--) {
                if (currentData.actual[i] !== null && currentData.actual[i] !== undefined) {
                    targetIdx = i;
                    break;
                }
            }
            if (targetIdx !== -1) {
                currentData.actual[targetIdx] = newPercentage;
            }
        }

        render(currentData);
    }

    async function refresh(event) {
        if (event && event.detail && event.detail.burndown) {
            latestRequest++;
            render(event.detail.burndown);
            return;
        }
        const requestId = ++latestRequest;
        try {
            const response = await fetch(canvas.dataset.url, { headers: { Accept: 'application/json' }, cache: 'no-store' });
            if (!response.ok) throw new Error('Progress request failed');
            const payload = await response.json();
            if (!payload.ok) throw new Error('Invalid progress response');
            if (requestId === latestRequest) render(payload.burndown);
        } catch (err) {
            if (requestId === latestRequest) showError('Progress could not refresh. Reload the page to try again.');
        }
    }

    render(JSON.parse(initialData.textContent));
    document.addEventListener('sprint-task-status-optimistic', handleOptimisticChange);
    document.addEventListener('sprint-task-status-changed', refresh);
    window.addEventListener('focus', refresh);
    window.refreshSprintBurndown = refresh;
});
