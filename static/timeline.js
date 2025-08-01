// API endpoints
const API_BASE_URL = 'http://localhost:5000/api';

// DOM Elements
const timelineContainer = document.getElementById('interactive-timeline');

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadTimeline();
});

// Modal Functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'block';
    modal.classList.add('open');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'none';
    modal.classList.remove('open');
}

// Allow modals to be closed by pressing Escape
window.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal').forEach(modal => {
            if (modal.style.display === 'block' || modal.classList.contains('open')) {
                closeModal(modal.id);
            }
        });
    }
});

// Helper function to get changed parameters between prints
function getChangedParams(current, previous) {
    if (!current || !previous) return new Set();
    const changed = new Set();
    for (const key in current) {
        if (current[key] !== previous[key]) {
            changed.add(key);
        }
    }
    return changed;
}

// Helper function to get color based on quality rating
function getQualityColor(rating) {
    if (!rating) return '#808080'; // Gray for no rating
    
    // Normalize rating to 0-1 range
    const normalizedRating = (rating - 1) / 9; // Assuming 1-10 scale
    
    // Color interpolation between red and green
    const red = Math.round(255 * (1 - normalizedRating));
    const green = Math.round(255 * normalizedRating);
    
    return `rgb(${red}, ${green}, 0)`;
}

// Timeline Functions
async function loadTimeline() {
    try {
        // Fetch both prints and maintenance events
        const [printsResponse, maintenanceResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/prints`),
            fetch(`${API_BASE_URL}/maintenance`)
        ]);
        
        const prints = await printsResponse.json();
        const maintenance = await maintenanceResponse.json();

        // Sort prints by start time
        prints.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

        // Create timeline items
        const items = new vis.DataSet([
            // Add print events
            ...prints.map((print, index) => {
                const previousPrint = index > 0 ? prints[index - 1] : null;
                const allParams = print.all_slicer_params || {};
                const previousParams = previousPrint ? previousPrint.all_slicer_params || {} : {};
                const changedParams = getChangedParams(allParams, previousParams);
                
                // Create a detailed tooltip showing parameter changes
                let tooltipContent = `Print: ${print.filename}\nStatus: ${print.status}\nQuality: ${print.quality_rating || 'N/A'}/10`;
                
                if (changedParams.size > 0) {
                    tooltipContent += '\n\nChanged Parameters:';
                    changedParams.forEach(param => {
                        const oldValue = previousParams[param] || 'N/A';
                        const newValue = allParams[param];
                        tooltipContent += `\n${param}: ${oldValue} → ${newValue}`;
                    });
                }

                const qualityColor = getQualityColor(print.quality_rating);
                
                return {
                    id: `print-${print.id}`,
                    content: `Print: ${print.filename}`,
                    start: new Date(print.start_time),
                    type: 'box',
                    className: 'print-event',
                    style: `background-color: ${qualityColor}; border-color: ${qualityColor}; color: white;`,
                    group: 'prints',
                    title: tooltipContent,
                    data: { 
                        type: 'print', 
                        id: print.id,
                        changedParams: Array.from(changedParams)
                    }
                };
            }),
            // Add maintenance events
            ...maintenance.map(maint => ({
                id: `maintenance-${maint.id}`,
                content: `Maintenance: ${maint.description.substring(0, 30)}${maint.description.length > 30 ? '...' : ''}`,
                start: new Date(maint.timestamp),
                type: 'box',
                className: 'maintenance-event',
                group: 'maintenance',
                title: `Maintenance: ${maint.description}`,
                data: { type: 'maintenance', id: maint.id }
            }))
        ]);

        // Create timeline groups with custom heights
        const groups = new vis.DataSet([
            { id: 'prints', content: 'Prints', height: 100 },
            { id: 'maintenance', content: 'Maintenance', height: 50 }
        ]);

        // Create timeline options
        const options = {
            height: '600px',
            stack: false,
            showMajorLabels: true,
            showCurrentTime: false,
            zoomable: true,
            moveable: true,
            orientation: 'top',
            groupHeightMode: 'fixed',
            clickToUse: true,
            margin: {
                item: {
                    horizontal: 10,
                    vertical: 5
                }
            },
            zoomMin: 1000 * 60 * 5, // 5 minutes in milliseconds
            zoomMax: 1000 * 60 * 60 * 24 * 365, // 1 year in milliseconds
            zoomFriction: 5,
            mousewheel: true,
            zoomSpeed: 0.5,
            verticalScroll: true,
            horizontalScroll: true,
            showTooltips: true,
            tooltip: {
                followMouse: true,
                overflowMethod: 'cap'
            },
            minHeight: 100,
            maxHeight: 800,
            zoomable: true,
            moveable: true,
            zoomMin: 1000 * 60 * 5, // 5 minutes
            zoomMax: 1000 * 60 * 60 * 24 * 365, // 1 year
            zoomFriction: 5,
            mousewheel: true,
            zoomSpeed: 0.5,
            verticalScroll: true,
            horizontalScroll: true,
            showTooltips: true,
            tooltip: {
                followMouse: true,
                overflowMethod: 'cap'
            }
        };

        // Create the timeline
        const timeline = new vis.Timeline(timelineContainer, items, groups, options);

        // Add zoom controls
        const zoomControls = document.createElement('div');
        zoomControls.className = 'timeline-controls';
        zoomControls.innerHTML = `
            <button class="timeline-control-btn" id="todayBtn">Today</button>
            <button class="timeline-control-btn" id="zoomInBtn">Zoom In</button>
            <button class="timeline-control-btn" id="zoomOutBtn">Zoom Out</button>
        `;
        timelineContainer.parentElement.insertBefore(zoomControls, timelineContainer);

        // Add click handlers for zoom controls
        document.getElementById('todayBtn').addEventListener('click', () => {
            timeline.moveTo(new Date());
        });

        document.getElementById('zoomInBtn').addEventListener('click', () => {
            const range = timeline.getWindow();
            const interval = range.end - range.start;
            const newInterval = interval * 0.5;
            const center = (range.start.getTime() + range.end.getTime()) / 2;
            timeline.setWindow(
                new Date(center - newInterval / 2),
                new Date(center + newInterval / 2)
            );
        });

        document.getElementById('zoomOutBtn').addEventListener('click', () => {
            const range = timeline.getWindow();
            const interval = range.end - range.start;
            const newInterval = interval * 2;
            const center = (range.start.getTime() + range.end.getTime()) / 2;
            timeline.setWindow(
                new Date(center - newInterval / 2),
                new Date(center + newInterval / 2)
            );
        });

        // Add click handler for timeline events
        timeline.on('click', function(properties) {
            if (properties.item) {
                const item = items.get(properties.item);
                if (item.data.type === 'print') {
                    showPrintDetailsModal(item.data.id, item.data.changedParams);
                } else if (item.data.type === 'maintenance') {
                    showMaintenanceDetailsModal(item.data.id);
                }
            }
        });

    } catch (error) {
        console.error('Error loading timeline:', error);
    }
}

// Show print details modal
async function showPrintDetailsModal(printId, changedParams) {
    try {
        const response = await fetch(`${API_BASE_URL}/prints`);
        const prints = await response.json();
        const print = prints.find(p => p.id == printId);
        if (!print) return;

        // Store the print ID for the save function
        document.getElementById('print-details-form').setAttribute('data-print-id', printId);

        // Populate the form fields
        document.getElementById('edit-quality-rating').value = print.quality_rating || '';
        document.getElementById('edit-functionality-rating').value = print.functionality_rating || '';
        document.getElementById('edit-label').value = print.label || 'structural';
        document.getElementById('edit-ambient-temp').value = print.ambient_temperature || '';
        document.getElementById('edit-ambient-humidity').value = print.ambient_humidity || '';
        document.getElementById('edit-notes').value = print.notes || '';

        // Slicer parameters section with changed parameters highlighted
        const allParams = print.all_slicer_params || {};
        const categories = [
            'filament', 'support', 'infill', 'printer', 'slicer', 'extruder', 'perimeter', 'layer', 'speed', 'temperature', 'cooling', 'retraction', 'skirt', 'raft', 'brim', 'adhesion', 'travel', 'wipe', 'fan', 'bed', 'object', 'top', 'bottom', 'shell', 'material', 'flow', 'acceleration', 'jerk', 'gcode', 'machine', 'tool', 'wall', 'seam', 'iron', 'bridge', 'prime', 'ooze', 'elephant', 'z', 'x', 'y', 'general'
        ];
        const groups = {};
        const other = [];
        for (const [key, value] of Object.entries(allParams)) {
            if (!key || value === undefined || value === null) continue;
            let found = false;
            for (const cat of categories) {
                if (key.toLowerCase().startsWith(cat)) {
                    if (!groups[cat]) groups[cat] = [];
                    groups[cat].push({ key, value });
                    found = true;
                    break;
                }
            }
            if (!found) {
                other.push({ key, value });
            }
        }
        let paramsHtml = '';
        if (groups['general']) {
            paramsHtml += `
            <div class="param-group">
                <div class="param-group-title">General</div>
                <ul class="param-list">
                    ${groups['general'].map(p => `<li class="${changedParams && changedParams.includes(p.key) ? 'changed-param' : ''}"><strong>${p.key}:</strong> ${p.value}</li>`).join('')}
                </ul>
            </div>
            `;
        }
        for (const cat of categories) {
            if (cat === 'general') continue;
            if (groups[cat]) {
                paramsHtml += `
                <div class="param-group">
                    <div class="param-group-title">${cat.charAt(0).toUpperCase() + cat.slice(1)}</div>
                    <ul class="param-list">
                        ${groups[cat].map(p => `<li class="${changedParams && changedParams.includes(p.key) ? 'changed-param' : ''}"><strong>${p.key}:</strong> ${p.value}</li>`).join('')}
                    </ul>
                </div>
                `;
            }
        }
        if (other.length > 0) {
            paramsHtml += `
            <div class="param-group">
                <div class="param-group-title">Other</div>
                <ul class="param-list">
                    ${other.map(p => `<li class="${changedParams && changedParams.includes(p.key) ? 'changed-param' : ''}"><strong>${p.key}:</strong> ${p.value}</li>`).join('')}
                </ul>
            </div>
            `;
        }
        document.getElementById('print-details-params').innerHTML = paramsHtml;

        openModal('print-details-modal');
    } catch (error) {
        console.error('Error showing print details:', error);
    }
}

// Add event listener for the print details form submission
document.getElementById('print-details-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const printId = this.getAttribute('data-print-id');
    const tempVal = document.getElementById('edit-ambient-temp').value;
    const humidityVal = document.getElementById('edit-ambient-humidity').value;
    
    const data = {
        quality_rating: document.getElementById('edit-quality-rating').value,
        functionality_rating: document.getElementById('edit-functionality-rating').value,
        label: document.getElementById('edit-label').value,
        ambient_temperature: tempVal === '' ? null : parseFloat(tempVal),
        ambient_humidity: humidityVal === '' ? null : parseFloat(humidityVal),
        notes: document.getElementById('edit-notes').value,
        status: 'success'
    };

    try {
        const response = await fetch(`${API_BASE_URL}/prints/${printId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('print-details-modal');
            // Reload the timeline to show updated data
            await loadTimeline();
        } else {
            throw new Error('Failed to update print');
        }
    } catch (error) {
        console.error('Error updating print:', error);
    }
});

// Show maintenance details modal
async function showMaintenanceDetailsModal(maintenanceId) {
    try {
        const response = await fetch(`${API_BASE_URL}/maintenance`);
        const maintenance = await response.json();
        const maint = maintenance.find(m => m.id == maintenanceId);
        if (!maint) return;

        // Store the maintenance ID for the save function
        document.getElementById('maintenance-details-form').setAttribute('data-maintenance-id', maintenanceId);

        // Populate the form fields
        document.getElementById('edit-maintenance-description').value = maint.description || '';
        document.getElementById('edit-maintenance-todo').value = maint.todo_tasks || '';

        openModal('maintenance-details-modal');
    } catch (error) {
        console.error('Error showing maintenance details:', error);
    }
}

// Add event listener for the maintenance details form submission
document.getElementById('maintenance-details-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const maintenanceId = this.getAttribute('data-maintenance-id');
    
    const data = {
        description: document.getElementById('edit-maintenance-description').value,
        todo_tasks: document.getElementById('edit-maintenance-todo').value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/maintenance/${maintenanceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('maintenance-details-modal');
            // Reload the timeline to show updated data
            await loadTimeline();
        } else {
            throw new Error('Failed to update maintenance event');
        }
    } catch (error) {
        console.error('Error updating maintenance event:', error);
    }
}); 