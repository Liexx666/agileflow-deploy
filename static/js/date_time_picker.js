/**
 * AgileFlow - Interactive Real Clock & Calendar Picker Engine
 * Provides visual clock face for time inputs and seamless calendar picker for date inputs.
 */
(function () {
    let activeTimeInput = null;
    let clockPickerModal = null;
    let currentHour = 9;
    let currentMinute = 30;
    let currentPeriod = 'AM';
    let currentMode = 'hours'; // 'hours' or 'minutes'
    let isDragging = false;

    function parse24TimeTo12(timeStr) {
        if (!timeStr || !timeStr.includes(':')) {
            const now = new Date();
            let h = now.getHours();
            const m = now.getMinutes();
            const p = h >= 12 ? 'PM' : 'AM';
            h = h % 12;
            if (h === 0) h = 12;
            return { hours: h, minutes: m, period: p };
        }
        const [hStr, mStr] = timeStr.split(':');
        let h = parseInt(hStr, 10);
        if (isNaN(h)) h = 9;
        let m = parseInt(mStr, 10);
        if (isNaN(m)) m = 0;
        const p = h >= 12 ? 'PM' : 'AM';
        h = h % 12;
        if (h === 0) h = 12;
        return { hours: h, minutes: m, period: p };
    }

    function format12TimeTo24(hours, minutes, period) {
        let h = parseInt(hours, 10);
        if (period === 'AM') {
            if (h === 12) h = 0;
        } else {
            if (h < 12) h += 12;
        }
        const hh = String(h).padStart(2, '0');
        const mm = String(minutes).padStart(2, '0');
        return `${hh}:${mm}`;
    }

    function createClockPickerDOM() {
        if (document.getElementById('agileflowClockPickerModal')) {
            return document.getElementById('agileflowClockPickerModal');
        }

        const backdrop = document.createElement('div');
        backdrop.id = 'agileflowClockPickerModal';
        backdrop.className = 'clock-picker-backdrop';
        backdrop.innerHTML = `
            <div class="clock-picker-dialog" role="dialog" aria-modal="true" aria-labelledby="clockPickerTitle">
                <div class="clock-picker-header">
                    <div class="clock-picker-title" id="clockPickerTitle">
                        <i class="bi bi-clock-fill me-1"></i> Choose Time
                    </div>
                    <div class="clock-picker-time-display">
                        <div class="clock-digits-wrap">
                            <button type="button" class="clock-display-btn active" id="clockDispBtnHours" title="Select Hours">09</button>
                            <span class="clock-display-colon">:</span>
                            <button type="button" class="clock-display-btn" id="clockDispBtnMinutes" title="Select Minutes">30</button>
                        </div>
                        <div class="clock-ampm-switch">
                            <button type="button" class="clock-ampm-btn active" id="clockBtnAM" data-period="AM">AM</button>
                            <button type="button" class="clock-ampm-btn" id="clockBtnPM" data-period="PM">PM</button>
                        </div>
                    </div>
                </div>
                <div class="clock-picker-body">
                    <div class="clock-face" id="clockFace">
                        <div class="clock-center-dot"></div>
                        <div class="clock-hand" id="clockHand">
                            <div class="clock-hand-line"></div>
                            <div class="clock-hand-pin"></div>
                        </div>
                        <div class="clock-numbers" id="clockNumbers"></div>
                    </div>
                </div>
                <div class="clock-picker-footer">
                    <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" id="clockBtnCancel">
                        Cancel
                    </button>
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" id="clockBtnNow">
                            Now
                        </button>
                        <button type="button" class="btn btn-sm btn-primary rounded-pill px-4 shadow-sm" id="clockBtnOK">
                            Set Time
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(backdrop);

        // Bind Controls
        document.getElementById('clockDispBtnHours').addEventListener('click', () => setMode('hours'));
        document.getElementById('clockDispBtnMinutes').addEventListener('click', () => setMode('minutes'));

        document.getElementById('clockBtnAM').addEventListener('click', () => {
            currentPeriod = 'AM';
            updateDisplay();
        });
        document.getElementById('clockBtnPM').addEventListener('click', () => {
            currentPeriod = 'PM';
            updateDisplay();
        });

        document.getElementById('clockBtnCancel').addEventListener('click', closeClockPicker);
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) closeClockPicker();
        });

        document.getElementById('clockBtnNow').addEventListener('click', () => {
            const now = new Date();
            let h = now.getHours();
            const m = now.getMinutes();
            currentPeriod = h >= 12 ? 'PM' : 'AM';
            h = h % 12;
            if (h === 0) h = 12;
            currentHour = h;
            currentMinute = m;
            updateDisplay();
            renderFace();
        });

        document.getElementById('clockBtnOK').addEventListener('click', () => {
            if (activeTimeInput) {
                const formatted = format12TimeTo24(currentHour, currentMinute, currentPeriod);
                activeTimeInput.value = formatted;
                activeTimeInput.dispatchEvent(new Event('input', { bubbles: true }));
                activeTimeInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
            closeClockPicker();
        });

        // Face pointer events (click / drag)
        const face = document.getElementById('clockFace');
        face.addEventListener('mousedown', (e) => {
            isDragging = true;
            handleClockInteraction(e);
        });
        window.addEventListener('mousemove', (e) => {
            if (isDragging) handleClockInteraction(e);
        });
        window.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                if (currentMode === 'hours') {
                    setTimeout(() => setMode('minutes'), 200);
                }
            }
        });

        // Touch support
        face.addEventListener('touchstart', (e) => {
            isDragging = true;
            handleClockInteraction(e.touches[0]);
        }, { passive: true });
        window.addEventListener('touchmove', (e) => {
            if (isDragging && e.touches.length > 0) handleClockInteraction(e.touches[0]);
        }, { passive: true });
        window.addEventListener('touchend', () => {
            if (isDragging) {
                isDragging = false;
                if (currentMode === 'hours') {
                    setTimeout(() => setMode('minutes'), 200);
                }
            }
        });

        // Keydown Esc/Enter
        window.addEventListener('keydown', (e) => {
            if (backdrop.classList.contains('show')) {
                if (e.key === 'Escape') closeClockPicker();
                if (e.key === 'Enter') document.getElementById('clockBtnOK').click();
            }
        });

        return backdrop;
    }

    function setMode(mode) {
        currentMode = mode;
        const btnH = document.getElementById('clockDispBtnHours');
        const btnM = document.getElementById('clockDispBtnMinutes');
        if (btnH && btnM) {
            btnH.classList.toggle('active', mode === 'hours');
            btnM.classList.toggle('active', mode === 'minutes');
        }
        renderFace();
    }

    function updateDisplay() {
        const btnH = document.getElementById('clockDispBtnHours');
        const btnM = document.getElementById('clockDispBtnMinutes');
        const btnAM = document.getElementById('clockBtnAM');
        const btnPM = document.getElementById('clockBtnPM');

        if (btnH) btnH.textContent = String(currentHour).padStart(2, '0');
        if (btnM) btnM.textContent = String(currentMinute).padStart(2, '0');

        if (btnAM && btnPM) {
            btnAM.classList.toggle('active', currentPeriod === 'AM');
            btnPM.classList.toggle('active', currentPeriod === 'PM');
        }
    }

    function renderFace() {
        const container = document.getElementById('clockNumbers');
        const hand = document.getElementById('clockHand');
        if (!container || !hand) return;

        container.innerHTML = '';
        const dialRadius = 86; // px
        const center = 115; // px

        if (currentMode === 'hours') {
            const angle = (currentHour % 12) * 30;
            hand.style.transform = `rotate(${angle}deg)`;

            for (let i = 1; i <= 12; i++) {
                const rad = ((i * 30 - 90) * Math.PI) / 180;
                const x = center + dialRadius * Math.cos(rad) - 16;
                const y = center + dialRadius * Math.sin(rad) - 16;

                const numEl = document.createElement('div');
                numEl.className = 'clock-num' + (i === currentHour ? ' selected' : '');
                numEl.style.left = `${x}px`;
                numEl.style.top = `${y}px`;
                numEl.textContent = i;
                numEl.dataset.value = i;
                container.appendChild(numEl);
            }
        } else {
            const angle = currentMinute * 6;
            hand.style.transform = `rotate(${angle}deg)`;

            const minuteMarks = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];
            minuteMarks.forEach((m) => {
                const rad = ((m * 6 - 90) * Math.PI) / 180;
                const x = center + dialRadius * Math.cos(rad) - 16;
                const y = center + dialRadius * Math.sin(rad) - 16;

                const numEl = document.createElement('div');
                numEl.className = 'clock-num' + (m === currentMinute ? ' selected' : '');
                numEl.style.left = `${x}px`;
                numEl.style.top = `${y}px`;
                numEl.textContent = String(m).padStart(2, '0');
                numEl.dataset.value = m;
                container.appendChild(numEl);
            });
        }
    }

    function handleClockInteraction(e) {
        const face = document.getElementById('clockFace');
        if (!face) return;

        const rect = face.getBoundingClientRect();
        const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
        const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);

        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = clientX - cx;
        const dy = clientY - cy;

        let deg = (Math.atan2(dy, dx) * 180) / Math.PI + 90;
        if (deg < 0) deg += 360;

        if (currentMode === 'hours') {
            let h = Math.round(deg / 30);
            if (h === 0) h = 12;
            currentHour = h;
        } else {
            let m = Math.round(deg / 6) % 60;
            currentMinute = m;
        }

        updateDisplay();
        renderFace();
    }

    function openClockPicker(input) {
        activeTimeInput = input;
        clockPickerModal = createClockPickerDOM();

        const parsed = parse24TimeTo12(input.value);
        currentHour = parsed.hours;
        currentMinute = parsed.minutes;
        currentPeriod = parsed.period;

        currentMode = 'hours';
        updateDisplay();
        setMode('hours');

        clockPickerModal.classList.add('show');
    }

    function closeClockPicker() {
        if (clockPickerModal) {
            clockPickerModal.classList.remove('show');
        }
    }

    function openDatePicker(input) {
        if (!input) return;
        if (typeof input.showPicker === 'function') {
            try {
                input.showPicker();
                return;
            } catch (err) {}
        }
        input.focus();
    }

    // Global Listeners for Date and Time pickers
    document.addEventListener('DOMContentLoaded', () => {
        // Date Inputs & Triggers
        document.addEventListener('click', (e) => {
            // Trigger calendar when clicking on date input
            const dateInput = e.target.closest('input[type="date"]');
            if (dateInput) {
                openDatePicker(dateInput);
                return;
            }

            // Trigger calendar from button
            const dateBtn = e.target.closest('.btn-date-picker-trigger');
            if (dateBtn) {
                e.preventDefault();
                e.stopPropagation();
                const group = dateBtn.closest('.input-group') || dateBtn.parentElement;
                const target = group ? group.querySelector('input[type="date"]') : null;
                if (target) openDatePicker(target);
                return;
            }

            // Trigger clock from button
            const clockBtn = e.target.closest('.btn-clock-picker-trigger');
            if (clockBtn) {
                e.preventDefault();
                e.stopPropagation();
                const group = clockBtn.closest('.input-group') || clockBtn.parentElement;
                const target = group ? group.querySelector('input[type="time"]') : null;
                if (target) openClockPicker(target);
                return;
            }

            // Trigger clock when clicking on time input
            const timeInput = e.target.closest('input[type="time"]');
            if (timeInput) {
                e.preventDefault();
                openClockPicker(timeInput);
                return;
            }
        });
    });

    // Expose helper on window
    window.AgileFlowClockPicker = {
        open: openClockPicker,
        close: closeClockPicker
    };
})();
