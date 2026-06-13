// Global state
let mapInstance;
let deckOverlay;
let allCases = [];
let allBoundaries = [];
let selectedBoundaryFeature = null;
let visibleDiseases = [];
let currentDatasetIndex = 0;
let dateRange = { min: 0, max: Date.now() };

let currentDisplayMode = 'cluster';
let spatialQueryEnabled = false;
let spatialQueryMarker = null;

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// DataTable Instance
let currentSliderIndex = 0;
let datasetsByDisease = {}; // store data for downloads

// Distinct Variant Color Palette
const COLORS = {
    'cholera': { base: '#0dcaf0', 'O1 Ogawa': '#0a58ca', 'O1 Inaba': '#3d8bfd', 'default': '#0dcaf0' },
    'tb': { base: '#dc3545', 'MDR-TB': '#842029', 'XDR-TB': '#5c161d', 'default': '#dc3545' },
    'hiv': { base: '#6f42c1', 'HIV-1': '#4a2b82', 'HIV-2': '#e0cffc', 'default': '#6f42c1' }
};

function stringToColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    let color = '#';
    for (let i = 0; i < 3; i++) {
        let value = (hash >> (i * 8)) & 0xFF;
        color += ('00' + value.toString(16)).substr(-2);
    }
    return color;
}

function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
    ] : [255, 0, 0];
}

function getColorForCase(disease, variant) {
    disease = disease.toLowerCase();
    if (COLORS[disease]) {
        if (variant && COLORS[disease][variant]) return COLORS[disease][variant];
        return COLORS[disease]['default'];
    }
    return stringToColor(variant ? disease + variant : disease);
}

function updateLegend() {
    const legendContent = document.getElementById('dynamic-legend-content');
    let html = '';
    
    visibleDiseases.forEach(d => {
        if (COLORS[d]) {
            const group = COLORS[d];
            html += `<div class="mb-2 fw-bold text-uppercase" style="color: ${group.base}">${d}</div>`;
            
            Object.keys(group).forEach(key => {
                if (key === 'base') return;
                const label = key === 'default' ? 'Unspecified Strain' : key;
                html += `
                    <div class="legend-item">
                        <div class="legend-color-box" style="background-color: ${group[key]};"></div>
                        <span>${label}</span>
                    </div>
                `;
            });
        } else {
            const color = getColorForCase(d, null);
            html += `<div class="mb-2 fw-bold text-uppercase" style="color: ${color}">${d}</div>`;
            html += `
                <div class="legend-item">
                    <div class="legend-color-box" style="background-color: ${color};"></div>
                    <span>Unspecified Strain</span>
                </div>
            `;
        }
    });
    
    legendContent.innerHTML = html || 'No data selected';
}

let visibleVariants = {};

const DISEASE_ICONS = {
    'cholera': 'bi-virus',
    'hiv': 'bi-activity',
    'tb': 'bi-lungs'
};

document.addEventListener('DOMContentLoaded', () => {
    // Initialize visibleDiseases array based on options
    const diseaseSelect = document.getElementById('global-disease-select');
    const variantSelect = document.getElementById('global-variant-select');
    
    if (diseaseSelect) {
        const diseaseOptions = Array.from(diseaseSelect.options);
        diseaseOptions.forEach(opt => {
            if (opt.value) {
                visibleDiseases.push(opt.value);
                visibleVariants[opt.value] = "";
            }
        });

        diseaseSelect.addEventListener('change', function() {
            const selectedDisease = this.value;
            if (selectedDisease === "") {
                // All diseases selected
                visibleDiseases = diseaseOptions.filter(o => o.value).map(o => o.value);
                variantSelect.innerHTML = '<option value="">All Variants</option>';
                variantSelect.disabled = true;
                // Clear all variant filters
                visibleDiseases.forEach(d => visibleVariants[d] = "");
            } else {
                // Specific disease selected
                visibleDiseases = [selectedDisease];
                variantSelect.disabled = false;
                variantSelect.innerHTML = '<option value="">All Variants</option>';
                // Populate variants for this disease if any
                if (COLORS[selectedDisease]) {
                    Object.keys(COLORS[selectedDisease]).forEach(variant => {
                        if (variant !== 'base' && variant !== 'default') {
                            const opt = document.createElement('option');
                            opt.value = variant;
                            opt.innerText = variant;
                            variantSelect.appendChild(opt);
                        }
                    });
                }
                // Clear other variant filters
                Object.keys(visibleVariants).forEach(d => visibleVariants[d] = "");
            }
            renderCases();
            updateLegend();
            updateDatasetTable();
        });

        if (variantSelect) {
            variantSelect.addEventListener('change', function() {
                const selectedDisease = diseaseSelect.value;
                if (selectedDisease) {
                    visibleVariants[selectedDisease] = this.value;
                    renderCases();
                    updateLegend();
                }
            });
        }
    }

    initMap();
    initMapSearch();
});

window.toggleDiseaseFilter = function(disease, element) {
    // Deprecated: Replaced by global dropdown
};

function initMap() {
    mapInstance = L.map('mainmap', {
        fullscreenControl: true,
        fullscreenControlOptions: {
            position: 'topleft'
        }
    }).setView([-19.0154, 29.1549], 6);

    // Fullscreen UX Handling
    mapInstance.on('enterFullscreen', function() {
        const mapContainer = document.getElementById('mainmap');
        const legend = document.querySelector('.map-legend-overlay');
        const filters = document.getElementById('map-status-filters');
        const timeSlider = document.getElementById('card-time-slider');
        
        if (legend) mapContainer.appendChild(legend);
        if (filters) mapContainer.appendChild(filters);
        if (timeSlider) {
            timeSlider.classList.add('fullscreen-filter-overlay', 'fs-time-slider');
            mapContainer.appendChild(timeSlider);
        }
    });

    mapInstance.on('exitFullscreen', function() {
        const wrapper = document.getElementById('map-wrapper');
        const sidePanel = document.querySelector('.side-panel');
        const legend = document.querySelector('.map-legend-overlay');
        const filters = document.getElementById('map-status-filters');
        const timeSlider = document.getElementById('card-time-slider');
        const actionButtons = sidePanel ? sidePanel.querySelector('.d-grid.gap-2.mt-auto') : null;
        
        if (legend && wrapper) wrapper.appendChild(legend);
        if (filters && wrapper) wrapper.appendChild(filters);
        if (timeSlider && sidePanel && actionButtons) {
            timeSlider.classList.remove('fullscreen-filter-overlay', 'fs-time-slider');
            sidePanel.insertBefore(timeSlider, actionButtons);
        }
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(mapInstance);
    
    deckOverlay = new DeckGlLeaflet.LeafletLayer({
        views: [new deck.MapView({repeat: true})],
        layers: []
    });
    mapInstance.addLayer(deckOverlay);

    // Fetch Administrative Boundaries
    fetch('/api/boundaries/?tolerance=0.01')
        .then(res => res.json())
        .then(data => {
            allBoundaries = data.features || (data.results && data.results.features) || data.results || [];
            
            window.boundaryLayer = L.geoJSON(data, {
                style: function(feature) {
                    return {
                        color: 'rgba(0,0,0,0.2)',
                        weight: 1,
                        fillColor: 'transparent',
                        fillOpacity: 0.0
                    };
                },
                onEachFeature: function(feature, layer) {
                    layer.on({
                        mouseover: function(e) {
                            var layer = e.target;
                            layer.setStyle({
                                weight: 2,
                                color: '#0dcaf0',
                                fillOpacity: 0.1
                            });
                        },
                        mouseout: function(e) {
                            if (!window.boundaryLayer) return;
                            window.boundaryLayer.resetStyle(e.target);
                        },
                        click: function(e) {
                            const p = e.target.feature.properties;
                            if (!p) return;
                            
                            const provSelect = $('#province-select');
                            const distSelect = $('#district-select');
                            
                            if (p.level === 'province') {
                                provSelect.val(p.id).trigger('change');
                            } else if (p.level === 'district') {
                                distSelect.val(p.id).trigger('change');
                            }
                        }
                    });
                }
            }).addTo(mapInstance);

            populateBoundaryDropdowns();
        });

    mapInstance.on('click', function(e) {
        if (!spatialQueryEnabled) return;
        handleSpatialQuery(e.latlng);
    });

    document.getElementById('btnShowcase').addEventListener('click', function() {
        const btn = this;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Loading Cases...';
        btn.disabled = true;
        
        fetch('/api/cases/')
            .then(res => {
                if (!res.ok) {
                    return res.json().then(err => { throw new Error(err.error || "Server Error"); }).catch(() => { throw new Error("Network/Server Error"); });
                }
                return res.json();
            })
            .then(data => {
                if (data.error) throw new Error(data.error);
                allCases = data.features || (data.results && data.results.features) || data.results || [];
                if (allCases.length === 0) {
                    alert('No cases found in database.');
                    btn.innerHTML = 'SHOWCASE';
                    btn.disabled = false;
                    return;
                }

                let minDate = new Date();
                let maxDate = new Date("2000-01-01");
                
                allCases.forEach(c => {
                    if (c.properties && c.properties.date_of_onset) {
                        const d = new Date(c.properties.date_of_onset);
                        if (d < minDate) minDate = d;
                        if (d > maxDate) maxDate = d;
                    }
                });
                
                // Dynamically extract variants
                const uniqueVariants = {};
                allCases.forEach(c => {
                    if (!c.properties) return;
                    const d = (c.properties.disease_type || "").toLowerCase();
                    const v = c.properties.variant;
                    if (!uniqueVariants[d]) uniqueVariants[d] = new Set();
                    if (v) uniqueVariants[d].add(v);
                });
                
                // Update global variant dropdown if a specific disease is selected
                const currentDisease = document.getElementById('global-disease-select')?.value;
                if (currentDisease && uniqueVariants[currentDisease]) {
                    const selectBox = document.getElementById('global-variant-select');
                    if (selectBox) {
                        uniqueVariants[currentDisease].forEach(v => {
                            if (v && v.trim() !== "") {
                                let exists = false;
                                for (let i = 0; i < selectBox.options.length; i++) {
                                    if (selectBox.options[i].value === v) { exists = true; break; }
                                }
                                if (!exists) {
                                    const opt = document.createElement('option');
                                    opt.value = v;
                                    opt.innerText = v;
                                    selectBox.appendChild(opt);
                                }
                            }
                        });
                    }
                }
                
                setupSlider(minDate.getTime(), maxDate.getTime());
                renderCases();
                updateLegend();
                
                btn.innerHTML = 'SHOWCASE';
                btn.classList.replace('btn-success', 'btn-secondary');
                
                startLiveCasePolling();
            })
            .catch(err => {
                alert('Error loading cases: ' + err);
                btn.innerHTML = 'SHOWCASE';
                btn.disabled = false;
            });
    });
}

function createPopupContent(feature) {
    const p = feature.properties;
    return `
        <div class="popup-header text-uppercase" style="color: ${getColorForCase(p.disease_type, p.variant)}">
            ${p.disease_type} Case
        </div>
        <div class="popup-detail">
            <strong>Variant:</strong> ${p.variant || 'Unspecified'}<br>
            <strong>Facility:</strong> ${p.facility__name || p.facility_name || 'Unknown'}<br>
            <strong>Location:</strong> ${p.location_name || 'Unknown'}<br>
            <strong>Reported:</strong> ${p.date_of_onset || 'Unknown Date'}<br>
            <strong>Demographics:</strong> Age ${p.age || 'N/A'}, Gender ${p.gender || 'U'}<br>
        </div>
    `;
}

function showPopup(feature, coordinate) {
    L.popup({closeOnClick: false})
        .setLatLng([coordinate[1], coordinate[0]])
        .setContent(createPopupContent(feature))
        .openOn(mapInstance);
}

// Live polling
let isPollingStarted = false;
let currentPollTimeout = null;
let lastPollTimestamp = new Date().toISOString();
const BASE_POLL_INTERVAL = 30000; // 30 seconds
let currentPollInterval = BASE_POLL_INTERVAL;

function pollLatestCases() {
    // 4. Pause polling when the browser tab is hidden using document.visibilityState
    if (document.visibilityState === 'hidden') {
        // Skip this execution and try again shortly without hitting the server
        currentPollTimeout = setTimeout(pollLatestCases, 5000);
        return;
    }

    fetch(`/api/latest-cases/?since=${encodeURIComponent(lastPollTimestamp)}`)
        .then(res => {
            if (!res.ok) throw new Error("Server Error");
            return res.json();
        })
        .then(data => {
            // 7. Reset exponential backoff on success
            currentPollInterval = BASE_POLL_INTERVAL;

            if (data.error) {
                console.warn("Polling error response:", data.error);
                // Continue loop
                currentPollTimeout = setTimeout(pollLatestCases, currentPollInterval);
                return;
            }
            const newCases = data.features || (data.results && data.results.features) || data.results || [];
            if (newCases.length > 0) {
                // Update timestamp
                let latestTime = new Date(lastPollTimestamp).getTime();
                
                const deduplicatedNewCases = newCases.filter(newCase => {
                    const existingIdx = allCases.findIndex(c => c.properties.id === newCase.properties.id);
                    if (existingIdx === -1) {
                        return true;
                    }
                    if (new Date(newCase.properties.updated_at) > new Date(allCases[existingIdx].properties.updated_at)) {
                        allCases[existingIdx] = newCase;
                    }
                    return false;
                });
                
                let newlyAddedCount = 0;
                deduplicatedNewCases.forEach(c => {
                    newlyAddedCount++;
                    allCases.push(c);
                    if (c.properties.created_at) {
                        const cTime = new Date(c.properties.created_at).getTime();
                        if (cTime > latestTime) latestTime = cTime;
                    }
                    if (c.geometry && c.geometry.coordinates) {
                        const lngLat = c.geometry.coordinates;
                        const popupHtml = `<div class="fw-bold text-success"><i class="bi bi-bell-fill"></i> New ${c.properties.disease_type.toUpperCase()} Case!</div>`;
                        L.popup({closeOnClick: false, autoClose: true})
                            .setLatLng([lngLat[1], lngLat[0]])
                            .setContent(popupHtml)
                            .openOn(mapInstance);
                    }
                });
                
                // 8. Ensure the 'since' timestamp is updated correctly
                lastPollTimestamp = new Date(latestTime).toISOString();
                
                if (newlyAddedCount > 0) {
                    if (latestTime > dateRange.max) {
                        const slider = document.getElementById('time-slider');
                        if (slider && slider.noUiSlider) {
                            let handles = slider.noUiSlider.get();
                            let rightHandle = parseInt(handles[1]);
                            let wasPegged = rightHandle >= dateRange.max - 2000; 
                            
                            slider.noUiSlider.updateOptions({
                                range: { 'min': dateRange.min, 'max': latestTime }
                            });
                            
                            if (wasPegged) {
                                slider.noUiSlider.set([handles[0], latestTime]);
                                dateRange.max = latestTime;
                            }
                        } else {
                            dateRange.max = latestTime;
                        }
                    }
                    
                    // 9. Only refetch/render if new cases detected
                    renderCases(); 
                    updateLegend();
                    updateDatasetTable();
                }
            }
            // Continue polling loop
            currentPollTimeout = setTimeout(pollLatestCases, currentPollInterval);
        })
        .catch(err => {
            console.error('Polling error:', err);
            // 7. Add exponential backoff if repeated errors occur (max 5 minutes)
            currentPollInterval = Math.min(currentPollInterval * 2, 300000);
            currentPollTimeout = setTimeout(pollLatestCases, currentPollInterval);
        });
}

function startLiveCasePolling() {
    // 1. & 2. Ensure polling is started only once and prevent duplicates
    if (isPollingStarted) return;
    isPollingStarted = true;
    
    if (currentPollTimeout) clearTimeout(currentPollTimeout);
    currentPollTimeout = setTimeout(pollLatestCases, currentPollInterval);
}

// 5. Resume polling aggressively when the tab becomes visible again
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && isPollingStarted) {
        if (currentPollTimeout) clearTimeout(currentPollTimeout);
        pollLatestCases();
    }
});

function getFilteredFeatures() {
    const severity = document.getElementById('filter-severity').value;
    const outcome  = document.getElementById('filter-outcome').value;

    return allCases.filter(c => {
        // Guard against invalid coordinates to prevent Deck.GL rendering crashes
        if (!c.geometry || !Array.isArray(c.geometry.coordinates) || c.geometry.coordinates.length < 2) return false;
        
        const lon = parseFloat(c.geometry.coordinates[0]);
        const lat = parseFloat(c.geometry.coordinates[1]);
        
        if (isNaN(lon) || isNaN(lat)) return false;
        
        // Strictly assign valid numbers
        c.geometry.coordinates[0] = lon;
        c.geometry.coordinates[1] = lat;
        
        const p = c.properties;
        if (!p) return false;
        
        const diseaseType = (p.disease_type || "").toLowerCase();

        let diseaseMatch = false;
        if (visibleDiseases.includes(diseaseType)) {
            const selectedVariant = visibleVariants[diseaseType];
            diseaseMatch = (!selectedVariant || selectedVariant === '') || (p.variant === selectedVariant);
        }

        const caseTime = p.date_of_onset ? new Date(p.date_of_onset).getTime() : null;
        const dateMatch = !caseTime || isNaN(caseTime) || (caseTime >= dateRange.min && caseTime <= dateRange.max);

        let geoMatch = true;
        
        // Add spatial pin drop radius filtering
        if (spatialQueryEnabled && window.spatialQueryPolygon && c.geometry && c.geometry.coordinates) {
            try {
                const pt = turf.point(c.geometry.coordinates);
                geoMatch = turf.booleanPointInPolygon(pt, window.spatialQueryPolygon);
            } catch(e) {
                geoMatch = true; // fail open
            }
        }

        let severityMatch = true;
        if (severity && severity !== '') severityMatch = (p.severity == severity);

        let outcomeMatch = true;
        if (outcome && outcome !== '') outcomeMatch = (p.outcome === outcome);

        return diseaseMatch && dateMatch && geoMatch && severityMatch && outcomeMatch;
    });
}


function renderCases() {
    const activeFeatures = getFilteredFeatures();
    
    // Clear existing cluster markers if they exist
    if (window.markersGroup) {
        mapInstance.removeLayer(window.markersGroup);
    }
    
    let deckLayers = [];

    if (currentDisplayMode === 'heatmap') {
        const heatRadius = parseInt(document.getElementById('heat-radius').value || 25);
        deckLayers.push(new deck.HeatmapLayer({
            id: 'heatmapLayer',
            data: activeFeatures,
            getPosition: d => d.geometry.coordinates,
            getWeight: d => d.properties.severity || 1,
            radiusPixels: heatRadius,
            intensity: 1,
            threshold: 0.05
        }));
    } else if (currentDisplayMode === 'raw') {
        deckLayers.push(new deck.ScatterplotLayer({
            id: 'rawPointsLayer',
            data: activeFeatures,
            getPosition: d => d.geometry.coordinates,
            getFillColor: d => hexToRgb(getColorForCase(d.properties.disease_type, d.properties.variant)),
            getRadius: d => 6,
            radiusUnits: 'pixels',
            opacity: 0.8,
            stroked: true,
            getLineColor: [255, 255, 255, 80],
            lineWidthMinPixels: 1,
            pickable: true,
            onHover: info => {
                const tooltip = document.getElementById('deck-tooltip');
                if (info.object) {
                    document.getElementById('mainmap').style.cursor = 'pointer';
                    tooltip.innerHTML = createPopupContent(info.object);
                    tooltip.style.display = 'block';
                    tooltip.style.left = info.x + 'px';
                    tooltip.style.top = info.y + 'px';
                } else {
                    document.getElementById('mainmap').style.cursor = '';
                    tooltip.style.display = 'none';
                }
            },
            onClick: info => {
                if (info.object) {
                    const tooltip = document.getElementById('deck-tooltip');
                    tooltip.style.display = 'none';
                    showPopup(info.object, info.coordinate);
                }
            }
        }));
    } else if (currentDisplayMode === 'cluster') {
        window.markersGroup = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: 50
        });
        
        activeFeatures.forEach(f => {
            let color = getColorForCase(f.properties.disease_type, f.properties.variant);
            let iconHtml = `<div style="background-color:${color}; width:16px; height:16px; border-radius:50%; border:2px solid #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3);"></div>`;
            let customIcon = L.divIcon({
                className: 'custom-leaflet-marker',
                html: iconHtml,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });
            let m = L.marker([f.geometry.coordinates[1], f.geometry.coordinates[0]], {icon: customIcon});
            m.bindPopup(createPopupContent(f));
            window.markersGroup.addLayer(m);
        });
        mapInstance.addLayer(window.markersGroup);
    }
    
    if (deckOverlay) {
        deckOverlay.setProps({ layers: deckLayers });
    }

    // Refresh spatial query if active
    if (spatialQueryEnabled && spatialQueryMarker) {
        const radiusKm = parseFloat(document.getElementById('query-radius').value);
        const count = activeFeatures.length;
        let diseaseCounts = {};
        activeFeatures.forEach(f => {
            const d = f.properties.disease_type;
            diseaseCounts[d] = (diseaseCounts[d] || 0) + 1;
        });
        
        let summaryHtml = `<div class="mb-2 fw-bold text-danger border-bottom pb-1">Radius Search: ${radiusKm}km</div>`;
        summaryHtml += `<div class="mb-2"><strong>Total Cases: </strong> ${count}</div>`;
        for (let [d, c] of Object.entries(diseaseCounts)) {
            summaryHtml += `<div class="mb-1"><span class="badge" style="background-color:${getColorForCase(d)}">${d.toUpperCase()}</span> : ${c}</div>`;
        }
        spatialQueryMarker.setPopupContent(summaryHtml);
    }
    updateDatasetTable(activeFeatures);
    updateTimeSeriesChart(activeFeatures);
    updateTrendAnalysis();
    updateCorrelationAnalysis();
}

// UI Event Listeners
document.querySelectorAll('input[name="displayMode"]').forEach(radio => {
    radio.addEventListener('change', function() {
        currentDisplayMode = this.value;
        const heatControls = document.getElementById('heatmap-controls');
        if (this.value === 'heatmap') {
            heatControls.classList.remove('d-none');
        } else {
            heatControls.classList.add('d-none');
        }
        renderCases();
    });
});

document.getElementById('heat-radius')?.addEventListener('input', function() {
    document.getElementById('heat-radius-val').innerText = this.value;
    if (currentDisplayMode === 'heatmap') renderCases();
});

// Previous disease toggles removed; using new disease-filter-row logic

// ─────────────────────────────────────────────────────────────
//  MAP SEARCH  (Nominatim / OpenStreetMap geocoding)
//  Initialised inside DOMContentLoaded so mapInstance is ready
// ─────────────────────────────────────────────────────────────
function initMapSearch() {
    const toggleBtn   = document.getElementById('btn-toggle-search');
    const searchPanel = document.getElementById('search-panel-container');
    const searchInput = document.getElementById('region-search-input');
    const closeBtn    = document.getElementById('btn-close-search');

    if (!toggleBtn || !searchPanel || !searchInput) {
        console.warn('[MapSearch] Required elements not found – search disabled.');
        return;
    }

    // --- Suggestion dropdown (appended below the search panel) ---
    const dropdown = document.createElement('div');
    dropdown.id = 'geocode-dropdown';
    Object.assign(dropdown.style, {
        position:    'absolute',
        top:         'calc(100% + 8px)',
        left:        '0',
        right:       '0',
        background:  '#fff',
        borderRadius:'16px',
        boxShadow:   '0 8px 32px rgba(0,0,0,0.18)',
        overflow:    'hidden',
        overflowY:   'auto',
        zIndex:      '99999',
        display:     'none',
        maxHeight:   '280px'
    });
    searchPanel.style.position = 'relative';
    searchPanel.appendChild(dropdown);

    // --- Marker for the located place ---
    let searchMarker = null;

    function clearSearchMarker() {
        if (searchMarker && mapInstance) {
            mapInstance.removeLayer(searchMarker);
            searchMarker = null;
        }
    }

    function flyToResult(result) {
        if (!mapInstance) return;
        const lat  = parseFloat(result.lat);
        const lon  = parseFloat(result.lon);
        const bbox = result.boundingbox; // [south, north, west, east]
        const displayName = result.display_name || '';
        const label = result.name || displayName.split(',')[0];

        clearSearchMarker();

        // Fit to bounding box when available, otherwise fly to point
        if (bbox && bbox.length === 4) {
            const south = parseFloat(bbox[0]), north = parseFloat(bbox[1]);
            const west  = parseFloat(bbox[2]), east  = parseFloat(bbox[3]);
            mapInstance.fitBounds([[south, west], [north, east]], { padding: [40, 40], maxZoom: 15 });
        } else {
            mapInstance.flyTo([lat, lon], 13, { animate: true, duration: 1.2 });
        }

        // Drop a styled pin
        searchMarker = L.marker([lat, lon], {
            icon: L.divIcon({
                className: '',
                html: `<div style="
                    background:#6366f1;color:#fff;font-size:12px;font-weight:700;
                    padding:5px 12px;border-radius:20px;white-space:nowrap;
                    box-shadow:0 3px 12px rgba(99,102,241,0.5);
                    border:2px solid #fff;max-width:240px;
                    overflow:hidden;text-overflow:ellipsis;
                ">
                    <i class="bi bi-geo-alt-fill" style="margin-right:4px;"></i>${label}
                </div>`,
                iconAnchor: [10, 10]
            })
        }).addTo(mapInstance);

        // Auto-clear pin after 8 seconds
        setTimeout(clearSearchMarker, 8000);

        dropdown.style.display = 'none';
        searchInput.value = label;
    }

    function renderDropdown(results) {
        if (!results || results.length === 0) {
            dropdown.innerHTML = `<div style="padding:14px 18px;color:#6b7280;font-size:13px;">
                <i class="bi bi-search me-2"></i>No results found
            </div>`;
            dropdown.style.display = 'block';
            return;
        }

        dropdown.innerHTML = results.map((r, i) => {
            const primary   = r.name || r.display_name.split(',')[0];
            const secondary = r.display_name.replace(primary + ', ', '').split(',').slice(0, 3).join(', ');
            const icon = r.type === 'administrative' || r.class === 'boundary' ? 'bi-map' :
                         r.class === 'place' ? 'bi-building' : 'bi-geo-alt';
            return `
                <div class="geocode-item" data-idx="${i}" style="
                    padding:10px 16px;cursor:pointer;
                    border-bottom:1px solid #f3f4f6;transition:background 0.12s;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <i class="bi ${icon}" style="color:#6366f1;flex-shrink:0;"></i>
                        <div>
                            <div style="font-weight:600;font-size:13px;color:#1e293b">${primary}</div>
                            <div style="font-size:11px;color:#94a3b8;margin-top:2px">${secondary}</div>
                        </div>
                    </div>
                </div>`;
        }).join('');
        dropdown.style.display = 'block';

        dropdown.querySelectorAll('.geocode-item').forEach((el, i) => {
            el.addEventListener('mouseenter', () => el.style.background = '#f0f0ff');
            el.addEventListener('mouseleave', () => el.style.background = '');
            el.addEventListener('mousedown', (e) => {
                // Use mousedown so it fires before input blur
                e.preventDefault();
                flyToResult(results[i]);
            });
        });
    }

    // --- Debounced Nominatim fetch ---
    let debounceTimer = null;
    let lastQuery     = '';
    let isLoading     = false;
    let abortCtrl     = null;

    function fetchSuggestions(query) {
        if (isLoading && abortCtrl) abortCtrl.abort();
        lastQuery = query;
        isLoading = true;
        abortCtrl = new AbortController();

        dropdown.innerHTML = `<div style="padding:12px 16px;color:#6b7280;font-size:13px;">
            <span class="spinner-border spinner-border-sm me-2"></span>Searching...
        </div>`;
        dropdown.style.display = 'block';

        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=8&accept-language=en`;

        fetch(url, {
            signal:  abortCtrl.signal,
            headers: { 'Accept-Language': 'en', 'User-Agent': 'ZimEpiTracker/1.0' }
        })
        .then(r => r.json())
        .then(data => { isLoading = false; renderDropdown(data); })
        .catch(err => {
            if (err.name === 'AbortError') return;
            isLoading = false;
            dropdown.innerHTML = `<div style="padding:12px 16px;color:#ef4444;font-size:13px;">
                <i class="bi bi-wifi-off me-2"></i>Search unavailable – check your connection.
            </div>`;
            dropdown.style.display = 'block';
        });
    }

    searchInput.addEventListener('input', function() {
        const q = this.value.trim();
        clearTimeout(debounceTimer);
        if (q.length < 2) { dropdown.style.display = 'none'; lastQuery = ''; return; }
        debounceTimer = setTimeout(() => fetchSuggestions(q), 380);
    });

    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(debounceTimer);
            const q = this.value.trim();
            if (q.length >= 2) fetchSuggestions(q);
        }
        if (e.key === 'Escape') closeSearch();
    });

    // Close dropdown on outside click
    document.addEventListener('click', function(e) {
        if (!searchPanel.contains(e.target) && e.target !== toggleBtn) {
            dropdown.style.display = 'none';
        }
    });

    // --- Open / close helpers ---
    function openSearch() {
        searchPanel.style.display = 'flex';   // flex keeps inner row aligned
        searchPanel.style.flexDirection = 'column';
        toggleBtn.style.background = '#6366f1';
        toggleBtn.style.color      = '#fff';
        toggleBtn.style.boxShadow  = '0 4px 16px rgba(99,102,241,0.45)';
        setTimeout(() => searchInput.focus(), 60);
    }

    function closeSearch() {
        searchPanel.style.display = 'none';
        dropdown.style.display    = 'none';
        toggleBtn.style.background = '';
        toggleBtn.style.color      = '';
        toggleBtn.style.boxShadow  = '';
        searchInput.value = '';
        lastQuery         = '';
        clearSearchMarker();
    }

    toggleBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        const isVisible = searchPanel.style.display && searchPanel.style.display !== 'none';
        isVisible ? closeSearch() : openSearch();
    });

    if (closeBtn) closeBtn.addEventListener('click', closeSearch);

    // Keyboard shortcut: Ctrl+F or just / to open search
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey && e.key === 'f') || (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA')) {
            e.preventDefault();
            openSearch();
        }
    });
}

// Spatial Query Setup
document.getElementById('toggle-spatial-query')?.addEventListener('change', function() {
    spatialQueryEnabled = this.checked;
    const ctrls = document.getElementById('spatial-query-controls');
    if (spatialQueryEnabled) {
        ctrls.classList.remove('d-none');
    } else {
        ctrls.classList.add('d-none');
        clearSpatialQuery();
    }
});

// Analytics Toggles
document.getElementById('toggle-trend')?.addEventListener('change', function() {
    const panel = document.getElementById('trend-analysis-panel');
    if (this.checked) {
        panel.style.display = 'block';
        updateTrendAnalysis();
    } else {
        panel.style.display = 'none';
    }
});
document.getElementById('btn-close-trend')?.addEventListener('click', function() {
    document.getElementById('toggle-trend').checked = false;
    document.getElementById('trend-analysis-panel').style.display = 'none';
});

document.getElementById('toggle-correlation')?.addEventListener('change', function() {
    const panel = document.getElementById('correlation-analysis-panel');
    if (this.checked) {
        panel.style.display = 'block';
        updateCorrelationAnalysis();
    } else {
        panel.style.display = 'none';
    }
});
document.getElementById('btn-close-correlation')?.addEventListener('click', function() {
    document.getElementById('toggle-correlation').checked = false;
    document.getElementById('correlation-analysis-panel').style.display = 'none';
});

document.querySelectorAll('.opacity-slider').forEach(slider => {
    slider.addEventListener('input', function() {
        const targetId = this.getAttribute('data-target');
        document.getElementById(targetId).style.opacity = this.value;
    });
});

document.getElementById('query-radius')?.addEventListener('input', function() {
    document.getElementById('query-radius-val').innerText = this.value;
    if (spatialQueryEnabled && spatialQueryMarker) {
        handleSpatialQuery(spatialQueryMarker.getLatLng());
    }
});

// ─────────────────────────────────────────────────────────────
//  TEMPORAL FILTER  (preset pills + month search)
// ─────────────────────────────────────────────────────────────
(function initTemporalFilter() {

    // --- Helpers ---
    function applyDateRange(min, max, badgeText) {
        dateRange = { min, max };
        renderCases();

        const slider = document.getElementById('time-slider');
        if (slider && slider.noUiSlider) {
            slider.noUiSlider.set([min, max]);
            updateSliderLabels(min, max);
        }

        const badge     = document.getElementById('temporal-active-badge');
        const badgeLbl  = document.getElementById('temporal-badge-text');
        if (badge && badgeLbl) {
            if (badgeText) {
                badgeLbl.textContent = badgeText;
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
        }
    }

    function applyPreset(val, label) {
        const now = Date.now();
        let minTime = 0;

        const DAY = 24 * 60 * 60 * 1000;
        if      (val === '1y')   minTime = now - 365  * DAY;
        else if (val === '180d') minTime = now - 180  * DAY;
        else if (val === '90d')  minTime = now - 90   * DAY;
        else if (val === '30d')  minTime = now - 30   * DAY;
        else if (val === '14d')  minTime = now - 14   * DAY;
        else if (val === '7d')   minTime = now - 7    * DAY;
        else if (val === 'all')  minTime = 0;

        const badgeText = val === 'all' ? null : label;
        applyDateRange(minTime, now, badgeText);
    }

    // --- Preset pill buttons ---
    document.querySelectorAll('.temporal-preset').forEach(btn => {
        btn.addEventListener('click', function () {
            // Update active style
            document.querySelectorAll('.temporal-preset').forEach(b => {
                b.classList.remove('active', 'btn-primary', 'btn-danger');
                b.classList.add('btn-outline-secondary');
            });
            this.classList.add('active');
            if (this.dataset.val === 'all') {
                this.classList.add('btn-danger');
                this.classList.remove('btn-outline-secondary');
            } else {
                this.classList.add('btn-primary');
                this.classList.remove('btn-outline-secondary');
            }

            // Clear month search box
            const monthInput = document.getElementById('month-search-input');
            if (monthInput) monthInput.value = '';

            applyPreset(this.dataset.val, this.textContent.trim());
        });
    });

    // --- Month search parser ---
    const MONTH_NAMES = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
    const MONTH_FULL  = ['january','february','march','april','may','june','july','august','september','october','november','december'];

    function parseMonthInput(raw) {
        const text = raw.trim().toLowerCase();
        let month = -1, year = -1;

        // "March 2026" / "Mar 2026"
        let m = text.match(/^([a-z]+)\s+(\d{2,4})$/);
        if (m) {
            const idx = MONTH_NAMES.indexOf(m[1].substring(0, 3));
            if (idx >= 0) { month = idx; year = parseInt(m[2]); }
        }

        // "2026 March" / "2026 Mar" (reversed)
        if (month < 0) {
            m = text.match(/^(\d{4})\s+([a-z]+)$/);
            if (m) {
                const idx = MONTH_NAMES.indexOf(m[2].substring(0, 3));
                if (idx >= 0) { month = idx; year = parseInt(m[1]); }
            }
        }

        // "March" alone — assume current year
        if (month < 0) {
            const idx = MONTH_FULL.indexOf(text);
            const idx2 = MONTH_NAMES.indexOf(text);
            if (idx >= 0)  { month = idx;  year = new Date().getFullYear(); }
            if (idx2 >= 0) { month = idx2; year = new Date().getFullYear(); }
        }

        // "3/2026", "03/2026", "3-2026"
        if (month < 0) {
            m = text.match(/^(\d{1,2})[\/\-](\d{2,4})$/);
            if (m) { month = parseInt(m[1]) - 1; year = parseInt(m[2]); }
        }

        // "2026-03", "2026/03"
        if (month < 0) {
            m = text.match(/^(\d{4})[\/\-](\d{1,2})$/);
            if (m) { year = parseInt(m[1]); month = parseInt(m[2]) - 1; }
        }

        if (month < 0 || year < 0) return null;
        if (year < 100) year += 2000;
        if (month < 0 || month > 11) return null;

        const start = new Date(year, month, 1).getTime();
        const end   = new Date(year, month + 1, 0, 23, 59, 59, 999).getTime(); // last ms of month
        const MONTH_LABELS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return { min: start, max: end, label: `${MONTH_LABELS[month]} ${year}` };
    }

    function applyMonthSearch() {
        const raw = (document.getElementById('month-search-input')?.value || '').trim();
        if (!raw) return;

        const result = parseMonthInput(raw);
        if (!result) {
            // Visual shake to indicate bad input
            const inp = document.getElementById('month-search-input');
            if (inp) {
                inp.classList.add('is-invalid');
                setTimeout(() => inp.classList.remove('is-invalid'), 1500);
            }
            return;
        }

        // Deactivate preset pills
        document.querySelectorAll('.temporal-preset').forEach(b => {
            b.classList.remove('active', 'btn-primary', 'btn-danger');
            b.classList.add('btn-outline-secondary');
        });

        applyDateRange(result.min, result.max, result.label);
    }

    // Enter key on month input
    document.getElementById('month-search-input')?.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); applyMonthSearch(); }
    });

    // Apply button
    document.getElementById('btn-apply-month')?.addEventListener('click', applyMonthSearch);

    // Clear / reset button inside active badge
    document.getElementById('btn-clear-temporal')?.addEventListener('click', function() {
        const monthInput = document.getElementById('month-search-input');
        if (monthInput) monthInput.value = '';

        // Re-activate "This Year" pill
        document.querySelectorAll('.temporal-preset').forEach(b => {
            b.classList.remove('active', 'btn-primary', 'btn-danger');
            b.classList.add('btn-outline-secondary');
        });
        const thisYearBtn = document.querySelector('.temporal-preset[data-val="1y"]');
        if (thisYearBtn) {
            thisYearBtn.classList.add('active', 'btn-primary');
            thisYearBtn.classList.remove('btn-outline-secondary');
        }

        const now = Date.now();
        applyDateRange(now - 365 * 24 * 60 * 60 * 1000, now, null);
    });

})();

// Initialise date range to 'This Year' (matching the default active pill)

(function() {
    const now = Date.now();
    dateRange = { min: now - (365 * 24 * 60 * 60 * 1000), max: now };
})();

function clearSpatialQuery() {
    if (spatialQueryMarker) {
        mapInstance.removeLayer(spatialQueryMarker);
        spatialQueryMarker = null;
    }
    if (window.spatialCircleLayer) {
        mapInstance.removeLayer(window.spatialCircleLayer);
        window.spatialCircleLayer = null;
    }
    window.spatialQueryPolygon = null;
    renderCases();
}

function handleSpatialQuery(latlng) {
    clearSpatialQuery();
    
    spatialQueryMarker = L.circleMarker(latlng, {
        color: '#dc3545', 
        radius: 6, 
        fillOpacity: 1
    }).addTo(mapInstance);
        
    const radiusKm = parseFloat(document.getElementById('query-radius').value);
    const center = [latlng.lng, latlng.lat];
    const options = {steps: 64, units: 'kilometers'};
    const circlePolygon = turf.circle(center, radiusKm, options);
    window.spatialQueryPolygon = circlePolygon;
    
    window.spatialCircleLayer = L.geoJSON(circlePolygon, {
        style: {
            color: '#dc3545',
            weight: 2,
            dashArray: '5, 5',
            fillOpacity: 0.1
        }
    }).addTo(mapInstance);
    
    // 1. Bind an empty spinner popup initially and open it so the user sees it loading
    spatialQueryMarker.bindPopup('<div class="d-flex align-items-center"><div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div><span>Calculating...</span></div>').openPopup();

    // 2. Use setTimeout to allow the browser to paint the spinner before starting the heavy filtering
    setTimeout(() => {
        renderCases(); // This will calculate everything and overwrite the spinner with the actual summary
    }, 50);
}

// Time Slider Setup
function setupSlider(minTime, maxTime) {
    // Update the global date range to cover all fetched data
    dateRange.min = minTime;
    dateRange.max = maxTime;

    const slider = document.getElementById('time-slider');
    // The slider widget is optional — the dashboard may use a dropdown instead
    if (!slider) {
        updateSliderLabels(minTime, maxTime);
        return;
    }

    if (slider.noUiSlider) {
        slider.noUiSlider.destroy();
    }

    noUiSlider.create(slider, {
        start: [minTime, maxTime],
        connect: true,
        range: {
            'min': minTime,
            'max': maxTime
        },
        step: 24 * 60 * 60 * 1000 // 1 day steps
    });

    updateSliderLabels(minTime, maxTime);

    slider.noUiSlider.on('slide', function (values) {
        dateRange.min = parseInt(values[0]);
        dateRange.max = parseInt(values[1]);
        updateSliderLabels(dateRange.min, dateRange.max);
        renderCases();
    });
}

function updateSliderLabels(min, max) {
    const startLabel = document.getElementById('date-start-label');
    const endLabel = document.getElementById('date-end-label');
    if (startLabel) startLabel.innerText = new Date(min).toLocaleDateString();
    if (endLabel) endLabel.innerText = new Date(max).toLocaleDateString();
}

// Dataset Upload
document.getElementById('uploadDiseaseSelection')?.addEventListener('change', function() {
    const val = this.value;
    const warningBox = document.getElementById('diseaseWarningBox');
    if (['cholera', 'tb', 'hiv'].includes(val)) {
        warningBox.classList.remove('d-none');
    } else {
        warningBox.classList.add('d-none');
    }
});

document.getElementById('btnSubmitUpload')?.addEventListener('click', function() {
    const diseaseSelect = document.getElementById('uploadDiseaseSelection');
    if (!diseaseSelect || !diseaseSelect.value) {
        alert("Please select a target disease type before importing.");
        return;
    }

    const fileInput = document.getElementById('datasetFile');
    if (fileInput.files.length === 0) {
        alert("Please select a file.");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('disease_type', diseaseSelect.value);

    document.getElementById('uploadSpinner').classList.remove('d-none');
    const feedback = document.getElementById('uploadFeedback');
    feedback.classList.remove('d-none', 'alert-success', 'alert-danger');
    feedback.classList.add('alert-info');
    feedback.innerText = "Uploading and processing data...";

    fetch('/api/upload/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('uploadSpinner').classList.add('d-none');
        if (data.status === 'success') {
            feedback.classList.replace('alert-info', 'alert-success');
            feedback.innerHTML = `<strong>Success!</strong> Imported ${data.records_imported} records.`;
            fileInput.value = "";
            
            setTimeout(() => {
                const modalEl = document.getElementById('uploadDatasetModal');
                const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                modal.hide();
                document.getElementById('btnShowcase').click();
            }, 1500);
        } else {
            feedback.classList.replace('alert-info', 'alert-danger');
            feedback.innerHTML = `<strong>Error:</strong> ${data.message || 'Validation failed.'}`;
        }
    })
    .catch(err => {
        document.getElementById('uploadSpinner').classList.add('d-none');
        feedback.classList.replace('alert-info', 'alert-danger');
        feedback.innerText = "Server error during upload.";
        console.error(err);
    });
});

// Dropdowns Filter Initialization
function populateBoundaryDropdowns() {
    const provSelect = document.getElementById('province-select');
    const distSelect = document.getElementById('district-select');

    if (!provSelect || !distSelect) return;

    // Destroy any existing Select2 before reinitialising
    if ($(provSelect).data('select2')) $(provSelect).select2('destroy');
    if ($(distSelect).data('select2')) $(distSelect).select2('destroy');

    provSelect.innerHTML = '<option value="">Loading provinces\u2026</option>';
    distSelect.innerHTML = '<option value="">Loading districts\u2026</option>';

    fetch('/api/regions/')
        .then(r => r.json())
        .then(data => {
            const provinces    = data.provinces    || [];
            const allDistricts = data.districts    || [];

            // -- Province dropdown --
            provSelect.innerHTML = '<option value=""></option>';
            provinces.forEach(p => {
                const opt = document.createElement('option');
                opt.value       = p.id;
                opt.textContent = p.name;
                provSelect.appendChild(opt);
            });

            // -- Helper: rebuild district list, optionally filtered by province --
            function renderDistricts(selectedProvId) {
                distSelect.innerHTML = '<option value=""></option>';
                allDistricts.forEach(d => {
                    if (selectedProvId) {
                        const matchById   = String(d.province_id) === String(selectedProvId);
                        const matchByName = provinces.find(
                            p => String(p.id) === String(selectedProvId) && p.name === d.province
                        );
                        // If the backend didn't supply province linkage, degrade gracefully and show it
                        if (d.province !== undefined || d.province_id !== undefined) {
                            if (!matchById && !matchByName) return;
                        }
                    }
                    const opt = document.createElement('option');
                    opt.value       = d.id;
                    opt.textContent = d.name;
                    distSelect.appendChild(opt);
                });
            }

            renderDistricts(null);  // all districts on first load

            const s2base = { 
                theme: 'bootstrap-5', 
                width: '100%', 
                allowClear: true,
                language: {
                    noResults: function() {
                        return "Region not found";
                    }
                }
            };

            $(provSelect).select2({ ...s2base, placeholder: 'All Provinces' });
            $(distSelect).select2({ ...s2base, placeholder: 'All Districts' });

            // Province selection cascades districts
            $(provSelect).on('select2:select select2:clear', function () {
                const pid = $(this).val() || '';
                renderDistricts(pid);

                if ($(distSelect).data('select2')) $(distSelect).select2('destroy');
                $(distSelect).select2({ ...s2base, placeholder: 'All Districts' });
                $(distSelect).val('').trigger('change.select2');

                $(distSelect).off('select2:select select2:clear').on('select2:select select2:clear', function () {
                    filterBoundaryLayer($(provSelect).val(), $(this).val());
                });

                filterBoundaryLayer(pid, '');
            });

            $(distSelect).on('select2:select select2:clear', function () {
                filterBoundaryLayer($(provSelect).val(), $(this).val());
            });

            document.getElementById('filter-severity')?.addEventListener('change', renderCases);
            document.getElementById('filter-outcome')?.addEventListener('change', renderCases);
        })
        .catch(err => {
            console.error('[Regions] Failed to load:', err);
            provSelect.innerHTML = '<option value="">All Provinces</option>';
            distSelect.innerHTML = '<option value="">All Districts</option>';
            $(provSelect).select2({ theme: 'bootstrap-5', width: '100%', placeholder: 'All Provinces', allowClear: true });
            $(distSelect).select2({ theme: 'bootstrap-5', width: '100%', placeholder: 'All Districts', allowClear: true });
        });
}

function filterBoundaryLayer(provId, distId) {
    if (!window.boundaryLayer) return;

    window.boundaryLayer.eachLayer(layer => {
        const p = layer.feature.properties;
        let show = true;
        
        if (distId && distId !== "") {
            show = (String(p.id) === String(distId));
        } else if (provId && provId !== "") {
            show = (String(p.id) === String(provId));
        }
        
        if (show) {
            if (!mapInstance.hasLayer(layer)) {
                mapInstance.addLayer(layer);
            }
        } else {
            if (mapInstance.hasLayer(layer)) {
                mapInstance.removeLayer(layer);
            }
        }
    });

    // Zoom to fit bounds
    let bounds = L.latLngBounds();
    window.boundaryLayer.eachLayer(layer => {
        if (mapInstance.hasLayer(layer)) {
            if (layer.getBounds) {
                bounds.extend(layer.getBounds());
            }
        }
    });
    
    // Only zoom if we have a specific selection AND bounds are valid
    if (bounds.isValid() && (distId !== "" || provId !== "")) {
        mapInstance.flyToBounds(bounds, {padding: [50, 50], maxZoom: 10, duration: 1.5});
    } else if (distId === "" && provId === "") {
        // Reset view to default if no region selected
        mapInstance.flyTo([-19.0154, 29.1549], 6, {duration: 1.5});
    }
}

// Interactive Data Table View
document.getElementById('btnToggleDataset')?.addEventListener('click', function() {
    const wrapper = document.getElementById('dataset-wrapper');
    const dragHandle = document.getElementById('dataset-drag-handle');
    
    if (wrapper.style.display === 'none') {
        wrapper.style.display = 'flex';
        wrapper.style.height = '40vh';
        dragHandle.style.display = 'flex';
        this.innerHTML = '<i class="bi bi-layout-split fs-5"></i> <span>Hide Dataset</span>';
        this.classList.replace('action-btn-gray', 'action-btn-outline');
        
        updateDatasetTable(getFilteredFeatures());
    } else {
        wrapper.style.display = 'none';
        this.innerHTML = '<i class="bi bi-layout-split fs-5"></i> <span>Show Dataset</span>';
        this.classList.replace('action-btn-outline', 'action-btn-gray');
    }
});

function updateDatasetTable(features) {
    const track = document.getElementById('dataset-slider-track');
    if (!track) return;
    
    track.innerHTML = '';
    datasetsByDisease = {};
    
    if (!features || features.length === 0 || visibleDiseases.length === 0) {
        track.innerHTML = '<div style="flex: 0 0 100%; width: 100%; padding: 20px; text-align: center;" class="text-muted">No records found.</div>';
        document.getElementById('dataset-title').innerText = 'Case Dataset';
        return;
    }

    visibleDiseases.forEach((disease, index) => {
        const diseaseFeatures = features.filter(f => f.properties.disease_type.toLowerCase() === disease.toLowerCase());
        datasetsByDisease[disease] = diseaseFeatures; // save for download
        
        const color = getColorForCase(disease);
        
        // Build table
        let tableHtml = `
            <div style="flex: 0 0 100%; width: 100%; height: 100%; overflow-y: auto; padding: 15px;">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="fw-bold" style="color: ${color}">${disease.toUpperCase()} Entries (${diseaseFeatures.length})</h6>
                    <button class="btn btn-sm btn-success shadow-sm" onclick="downloadDiseaseCSV('${disease}')">
                        <i class="bi bi-download me-1"></i> Download ${disease.toUpperCase()} CSV
                    </button>
                </div>
                <table class="table table-striped table-hover small" style="width:100%; border: 1px solid #dee2e6;">
                    <thead style="position: sticky; top: 0; background: #f8f9fa; z-index: 1;">
                        <tr>
                            <th>ID</th><th>Disease</th><th>Variant</th><th>Facility</th><th>Location</th><th>Date of Onset</th><th>Severity</th><th>Outcome</th><th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        if (diseaseFeatures.length === 0) {
            tableHtml += `<tr><td colspan="9" class="text-center text-muted py-3">No cases found for ${disease}</td></tr>`;
        } else {
            diseaseFeatures.forEach(f => {
                const p = f.properties;
                tableHtml += `
                    <tr>
                        <td><strong>#${p.id}</strong></td>
                        <td><span class="badge" style="background-color: ${color}">${p.disease_type.toUpperCase()}</span></td>
                        <td>${p.variant || '-'}</td>
                        <td><span class="small fw-bold text-muted">${p.facility__name || p.facility_name || '-'}</span></td>
                        <td>${p.location_name || '-'}</td>
                        <td>${p.date_of_onset || '-'}</td>
                        <td>${p.severity || '-'}</td>
                        <td>${p.outcome || '-'}</td>
                        <td><button class="btn btn-sm btn-outline-primary py-0 px-2 shadow-sm" onclick="zoomToCase(${f.geometry.coordinates[0]}, ${f.geometry.coordinates[1]})"><i class="bi bi-crosshair"></i> Locate</button></td>
                    </tr>
                `;
            });
        }
        
        tableHtml += `</tbody></table></div>`;
        track.innerHTML += tableHtml;
    });
    
    // Ensure index is valid
    if (currentSliderIndex >= visibleDiseases.length) {
        currentSliderIndex = Math.max(0, visibleDiseases.length - 1);
    }
    
    updateSliderUI();
}

function updateSliderUI() {
    const track = document.getElementById('dataset-slider-track');
    const title = document.getElementById('dataset-title');
    if (!track || visibleDiseases.length === 0) return;
    
    track.style.transform = `translateX(-${currentSliderIndex * 100}%)`;
    title.innerText = visibleDiseases[currentSliderIndex].toUpperCase() + ' Dataset';
}

document.getElementById('btnSlideLeft')?.addEventListener('click', function() {
    if (visibleDiseases.length <= 1) return;
    currentSliderIndex = (currentSliderIndex > 0) ? currentSliderIndex - 1 : visibleDiseases.length - 1;
    updateSliderUI();
});

document.getElementById('btnSlideRight')?.addEventListener('click', function() {
    if (visibleDiseases.length <= 1) return;
    currentSliderIndex = (currentSliderIndex < visibleDiseases.length - 1) ? currentSliderIndex + 1 : 0;
    updateSliderUI();
});

window.downloadDiseaseCSV = function(disease) {
    const features = datasetsByDisease[disease];
    if (!features || features.length === 0) {
        alert("No data available to download.");
        return;
    }
    
    let csvContent = "data:text/csv;charset=utf-8,";
    const headers = ['ID', 'Disease', 'Variant', 'Facility', 'Location', 'Date of Onset', 'Severity', 'Outcome', 'Coordinates'];
    csvContent += headers.join(",") + "\\r\\n";
    
    features.forEach(f => {
        const p = f.properties;
        const coords = f.geometry && f.geometry.coordinates ? `"${f.geometry.coordinates[1]}, ${f.geometry.coordinates[0]}"` : "N/A";
        const row = [
            p.id,
            p.disease_type,
            p.variant || '',
            (p.facility__name || p.facility_name || '').replace(/"/g, '""'),
            (p.location_name || '').replace(/"/g, '""'),
            p.date_of_onset || '',
            p.severity || '',
            p.outcome || '',
            coords
        ];
        csvContent += row.map(v => `"${v}"`).join(",") + "\r\n";
    });
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", disease + "_dataset.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

window.zoomToCase = function(lng, lat) {
    mapInstance.setView([lat, lng], 14, {animate: true});
    L.popup({closeOnClick: true})
        .setLatLng([lat, lng])
        .setContent(`<div class="fw-bold">Case Located</div>`)
        .openOn(mapInstance);
};

// Resizable Drawer Logic
const dragHandle = document.getElementById('dataset-drag-handle');
const datasetWrapper = document.getElementById('dataset-wrapper');
let isDragging = false;
let startY, startHeight;

if (dragHandle) {
    dragHandle.addEventListener('mousedown', function(e) {
        isDragging = true;
        startY = e.clientY;
        startHeight = parseInt(window.getComputedStyle(datasetWrapper).height, 10);
        document.body.style.cursor = 'ns-resize';
        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        const dy = startY - e.clientY;
        const newHeight = startHeight + dy;
        const maxHeight = window.innerHeight - 60; // Leave space for navbar
        
        if (newHeight >= 100 && newHeight <= maxHeight) {
            datasetWrapper.style.flex = `0 0 ${newHeight}px`;
            datasetWrapper.style.height = `${newHeight}px`;
        }
    });

    document.addEventListener('mouseup', function() {
        if (isDragging) {
            isDragging = false;
            document.body.style.cursor = 'default';
        }
    });
}

// Dataset Header Buttons functionality
document.getElementById('btnCloseDataset')?.addEventListener('click', function() {
    document.getElementById('btnToggleDataset').click();
});

document.getElementById('btnFullscreenDataset')?.addEventListener('click', function() {
    const wrapper = document.getElementById('dataset-wrapper');
    const dragHandle = document.getElementById('dataset-drag-handle');
    
    if (wrapper.classList.contains('fullscreen-dataset')) {
        wrapper.classList.remove('fullscreen-dataset');
        wrapper.style.position = 'relative';
        wrapper.style.height = '40vh';
        wrapper.style.zIndex = 'auto';
        dragHandle.style.display = 'flex';
        this.innerHTML = '<i class="bi bi-arrows-fullscreen"></i>';
    } else {
        wrapper.classList.add('fullscreen-dataset');
        wrapper.style.position = 'fixed';
        wrapper.style.top = '0';
        wrapper.style.left = '0';
        wrapper.style.width = '100vw';
        wrapper.style.height = '100vh';
        wrapper.style.zIndex = '10500';
        dragHandle.style.display = 'none';
        this.innerHTML = '<i class="bi bi-fullscreen-exit"></i>';
    }
});

// Removed old tabs and datatable filter logic completely

// --- Time Series Chart Logic ---
let timeSeriesChart = null;

/**
 * Epidemiological week key: "YYYY-Www"  (ISO-8601 week)
 * Returns { key: "2026-W19", label: "W19 2026" }
 */
function getEpiWeek(dateObj) {
    // Clone and shift to nearest Thursday (ISO week rule)
    const d = new Date(Date.UTC(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate()));
    const day = d.getUTCDay() || 7;          // Mon=1 … Sun=7
    d.setUTCDate(d.getUTCDate() + 4 - day);  // set to Thursday
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    const yr   = d.getUTCFullYear();
    return {
        key:   `${yr}-W${String(week).padStart(2, '0')}`,
        label: `W${String(week).padStart(2, '0')} ${yr}`,
        sort:  yr * 100 + week
    };
}

/**
 * 4-period Exponential Moving Average — the standard epidemiological
 * smoothing used by WHO/PAHO outbreak curves to distinguish signal from noise.
 * Alpha = 2/(N+1) where N = 4 weeks.
 */
function calcEMA(data, period) {
    const alpha = 2 / (period + 1);
    const ema   = new Array(data.length).fill(null);
    let seed = -1;
    // Find first non-null value to seed EMA
    for (let i = 0; i < data.length; i++) {
        if (data[i] !== null && data[i] !== undefined) { seed = i; break; }
    }
    if (seed < 0) return ema;
    ema[seed] = data[seed];
    for (let i = seed + 1; i < data.length; i++) {
        if (data[i] === null || data[i] === undefined) {
            ema[i] = ema[i - 1]; // carry forward through gaps
        } else {
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1];
        }
    }
    return ema;
}

function updateTimeSeriesChart(features) {
    const ctx = document.getElementById('timeseriesChart');
    if (!ctx) return;

    if (!features || features.length === 0) {
        if (timeSeriesChart) {
            timeSeriesChart.data.labels   = [];
            timeSeriesChart.data.datasets = [];
            timeSeriesChart.update('none');
        }
        return;
    }

    // ── 1. Aggregate case counts by ISO epi-week and disease ──────────────
    const weekMap      = {};  // key → { label, sort, counts: { disease: n } }
    const diseasesSet  = new Set();

    features.forEach(f => {
        const raw = f.properties.date_of_onset;
        if (!raw) return;
        const disease = f.properties.disease_type.toLowerCase();
        const epi     = getEpiWeek(new Date(raw));

        if (!weekMap[epi.key]) weekMap[epi.key] = { label: epi.label, sort: epi.sort, counts: {} };
        weekMap[epi.key].counts[disease] = (weekMap[epi.key].counts[disease] || 0) + 1;
        diseasesSet.add(disease);
    });

    const sortedWeeks  = Object.values(weekMap).sort((a, b) => a.sort - b.sort);
    const labels       = sortedWeeks.map(w => w.label);
    const diseases     = Array.from(diseasesSet);

    // ── 2. Build datasets: raw epi-curve line + EMA trend overlay ─────────
    const datasets = [];

    diseases.forEach(disease => {
        const color    = getColorForCase(disease, null);
        const rawCounts = sortedWeeks.map(w => w.counts[disease] || 0);
        const emaCounts = calcEMA(rawCounts, 4);

        // Raw incidence curve — thin, low-opacity filled area (the "epi-curve" bar equivalent)
        datasets.push({
            label:             disease.toUpperCase(),
            data:              rawCounts,
            borderColor:       color + 'aa',      // semi-transparent
            backgroundColor:   color + '18',      // very light fill
            borderWidth:       1.5,
            fill:              true,
            tension:           0.35,
            pointRadius:       0,                 // NO dots — pure line
            pointHoverRadius:  4,
            spanGaps:          true,
            order:             2,                 // draw behind EMA
        });

        // 4-week EMA trend line — solid, prominent, no fill (the meaningful trend)
        datasets.push({
            label:             disease.toUpperCase() + ' (4w trend)',
            data:              emaCounts,
            borderColor:       color,
            backgroundColor:   'transparent',
            borderWidth:       2.5,
            fill:              false,
            tension:           0.45,
            pointRadius:       0,
            pointHoverRadius:  5,
            borderDash:        [],                // solid trend line
            spanGaps:          true,
            order:             1,                 // draw on top
        });
    });

    // ── 3. Chart options ──────────────────────────────────────────────────
    const chartOptions = {
        responsive:          true,
        maintainAspectRatio: false,
        animation:           { duration: 400 },
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    boxWidth:       10,
                    usePointStyle:  true,
                    pointStyle:     'line',
                    font:           { size: 10, family: 'Inter, sans-serif' },
                    // Hide the raw-curve entries; only show trend lines in legend
                    filter: (item) => item.text.includes('trend')
                }
            },
            tooltip: {
                mode:      'index',
                intersect: false,
                callbacks: {
                    title: (items) => `Epi-week: ${items[0]?.label || ''}`,
                    label: (item) => {
                        // Only show tooltip rows for raw counts, not EMA (avoid duplication)
                        if (item.dataset.label.includes('trend')) return null;
                        const val = Math.round(item.parsed.y);
                        return ` ${item.dataset.label}: ${val} case${val !== 1 ? 's' : ''}`;
                    },
                    afterBody: (items) => {
                        // Show EMA value as annotation in tooltip
                        const lines = [];
                        items.forEach(item => {
                            if (!item.dataset.label.includes('trend')) {
                                const emaDs = items.find(i =>
                                    i.dataset.label === item.dataset.label + ' (4w trend)'
                                );
                                // Find EMA dataset manually
                                const idx   = item.dataIndex;
                                const ds    = timeSeriesChart?.data?.datasets;
                                if (ds) {
                                    const trendDs = ds.find(d =>
                                        d.label === item.dataset.label + ' (4w trend)'
                                    );
                                    if (trendDs && trendDs.data[idx] != null) {
                                        lines.push(`  4w EMA: ${trendDs.data[idx].toFixed(1)}`);
                                    }
                                }
                            }
                        });
                        return lines;
                    }
                },
                backgroundColor: 'rgba(255,255,255,0.95)',
                titleColor:      '#1e293b',
                bodyColor:       '#475569',
                borderColor:     '#e2e8f0',
                borderWidth:     1,
                padding:         10,
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                title: {
                    display:  true,
                    text:     'Reported Cases',
                    font:     { size: 10, weight: '600' },
                    color:    '#94a3b8'
                },
                ticks: {
                    precision: 0,
                    font:      { size: 10 },
                    color:     '#94a3b8'
                },
                grid: { color: '#f1f5f9' }
            },
            x: {
                grid:  { display: false },
                ticks: {
                    font:          { size: 9 },
                    color:         '#94a3b8',
                    maxRotation:   45,
                    autoSkip:      true,
                    maxTicksLimit: 20   // prevent x-axis crowding
                }
            }
        },
        interaction: { mode: 'index', axis: 'x', intersect: false }
    };

    if (timeSeriesChart) {
        timeSeriesChart.data.labels   = labels;
        timeSeriesChart.data.datasets = datasets;
        timeSeriesChart.options       = chartOptions;
        timeSeriesChart.update('active');
    } else {
        timeSeriesChart = new Chart(ctx, {
            type:    'line',
            data:    { labels, datasets },
            options: chartOptions
        });
    }
}





// Chart Toggle functionality
document.getElementById('btn-toggle-chart')?.addEventListener('click', function() {
    const panel = document.getElementById('timeseries-chart-panel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        setTimeout(() => {
            if (timeSeriesChart) timeSeriesChart.resize();
        }, 100);
    } else {
        panel.style.display = 'none';
    }
});
document.getElementById('btn-close-chart')?.addEventListener('click', function() {
    document.getElementById('timeseries-chart-panel').style.display = 'none';
});



// Status Filters Toggle functionality
document.getElementById('btn-toggle-filters')?.addEventListener('click', function() {
    const panel = document.getElementById('map-status-filters');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
    } else {
        panel.style.display = 'none';
    }
});
document.getElementById('btn-close-filters')?.addEventListener('click', function() {
    document.getElementById('map-status-filters').style.display = 'none';
});

// Legend Toggle functionality
document.getElementById('btn-toggle-legend')?.addEventListener('click', function() {
    const panel = document.querySelector('.map-legend-overlay');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
    } else {
        panel.style.display = 'none';
    }
});
document.getElementById('btn-close-legend')?.addEventListener('click', function() {
    document.querySelector('.map-legend-overlay').style.display = 'none';
});

// --- Advanced Analytics Logic ---

let trendAnalysisChart = null;
let correlationAnalysisChart = null;

// EMA Alpha parameter configuration
window.EMA_ALPHA = 0.4; // Default standard PAHO 4-week alpha

function calculateEMA(data, alpha) {
    if (data.length === 0) return [];
    let result = [data[0]];
    for (let i = 1; i < data.length; i++) {
        let prev = result[i - 1] === null ? 0 : result[i - 1];
        let curr = data[i] === null ? prev : data[i];
        result.push((curr * alpha) + (prev * (1 - alpha)));
    }
    return result;
}

function calculateLinearRegression(x, y) {
    const n = y.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
    
    for (let i = 0; i < n; i++) {
        sumX += x[i];
        sumY += y[i];
        sumXY += x[i] * y[i];
        sumX2 += x[i] * x[i];
    }
    
    // Handle edge case where n is small or sumX2 == sumX*sumX
    const denominator = n * sumX2 - sumX * sumX;
    if (denominator === 0) return { slope: 0, intercept: sumY / (n || 1) };
    
    const slope = (n * sumXY - sumX * sumY) / denominator;
    const intercept = (sumY - slope * sumX) / n;
    
    return { slope, intercept };
}

function calculateEMA(data, alpha) {
    if (data.length === 0) return [];
    let result = [data[0]];
    for (let i = 1; i < data.length; i++) {
        result.push((data[i] * alpha) + (result[i - 1] * (1 - alpha)));
    }
    return result;
}

function updateTrendAnalysis() {
    const panel = document.getElementById('trend-analysis-panel');
    if (!panel || panel.style.display === 'none') return;
    
    const features = getFilteredFeatures();
    if (features.length === 0) {
        document.getElementById('trend-summary-text').innerText = "Not enough data for trend analysis.";
        if (trendAnalysisChart) trendAnalysisChart.destroy();
        return;
    }
    
    // Group by week
    let weeklyCounts = {};
    features.forEach(f => {
        const d = new Date(f.properties.date_of_onset);
        const year = d.getFullYear();
        const start = new Date(year, 0, 1);
        const diff = d - start + (start.getTimezoneOffset() - d.getTimezoneOffset()) * 60 * 1000;
        const oneWeek = 1000 * 60 * 60 * 24 * 7;
        const week = Math.floor(diff / oneWeek);
        const key = `${year}-W${week.toString().padStart(2, '0')}`;
        weeklyCounts[key] = (weeklyCounts[key] || 0) + 1;
    });
    
    const sortedKeys = Object.keys(weeklyCounts).sort();
    let xValues = Array.from({length: sortedKeys.length}, (_, i) => i);
    let yValues = sortedKeys.map(k => weeklyCounts[k]);
    
    // Detect active week
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentStart = new Date(currentYear, 0, 1);
    const currentDiff = now - currentStart + (currentStart.getTimezoneOffset() - now.getTimezoneOffset()) * 60 * 1000;
    const currentWeek = Math.floor(currentDiff / (1000 * 60 * 60 * 24 * 7));
    const currentWeekKey = `${currentYear}-W${currentWeek.toString().padStart(2, '0')}`;
    
    let hasIncompleteWeek = false;
    if (sortedKeys.length > 0 && sortedKeys[sortedKeys.length - 1] === currentWeekKey) {
        hasIncompleteWeek = true;
    }
    
    if (xValues.length < 2) {
        document.getElementById('trend-summary-text').innerText = "Need at least two weeks of data for trend analysis.";
        if (trendAnalysisChart) trendAnalysisChart.destroy();
        return;
    }
    
    const emaLine = calculateEMA(yValues, window.EMA_ALPHA); 
    
    // OLS on EMA (exclude active week if present)
    const olsLength = hasIncompleteWeek ? xValues.length - 1 : xValues.length;
    const olsX = xValues.slice(0, olsLength);
    const olsY = emaLine.slice(0, olsLength);
    
    let regLine = new Array(xValues.length).fill(null);
    let trendDirection = "stable";
    let slopeVal = 0;
    
    if (olsX.length >= 2) {
        const reg = calculateLinearRegression(olsX, olsY);
        slopeVal = reg.slope;
        
        // Draw trendline for all xValues
        for(let i = 0; i < xValues.length; i++) {
            regLine[i] = reg.slope * xValues[i] + reg.intercept;
        }
        trendDirection = reg.slope > 0 ? "increasing" : "decreasing";
    }
    
    document.getElementById('trend-summary-text').innerHTML = `
        <span class="${slopeVal > 0 ? 'text-danger' : 'text-success'} fw-bold">
            ${slopeVal > 0 ? '<i class="bi bi-graph-up-arrow"></i>' : '<i class="bi bi-graph-down-arrow"></i>'}
            Recent ${trendDirection} trend
        </span> 
        (avg change of ${Math.abs(slopeVal).toFixed(2)} cases/week).
    `;
    
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (trendAnalysisChart) trendAnalysisChart.destroy();
    
    const barBackgroundColors = yValues.map((_, i) => (i === yValues.length - 1 && hasIncompleteWeek) ? '#fae8e4' : '#e2e8f0');
    const borderColors = yValues.map((_, i) => (i === yValues.length - 1 && hasIncompleteWeek) ? '#e6b8af' : '#64748b');

    let datasets = [
        {
            type: 'bar',
            label: 'Raw weekly cases Y_t',
            data: yValues,
            backgroundColor: barBackgroundColors,
            borderColor: borderColors,
            borderWidth: 1
        },
        {
            type: 'line',
            label: '4-period EMA (α = 0.4)',
            data: emaLine,
            borderColor: '#008080',
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: '#008080',
            fill: false,
            tension: 0.3
        },
        {
            type: 'line',
            label: `OLS trend on EMA (slope m = ${slopeVal > 0 ? '+' : ''}${slopeVal.toFixed(2)}, active week truncated)`,
            data: regLine,
            borderColor: '#c2410c',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false
        }
    ];

    if (hasIncompleteWeek) {
        datasets.unshift({
            type: 'bar',
            label: 'Active (incomplete) epi-week — excluded from OLS',
            data: [], // empty, just for legend
            backgroundColor: '#fae8e4',
            borderColor: '#fae8e4',
            borderWidth: 1
        });
    }

    trendAnalysisChart = new Chart(ctx, {
        data: {
            labels: sortedKeys.map(k => k.split('-W')[1]),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { 
                    position: 'top', 
                    labels: { boxWidth: 12, font: {size: 10} } 
                } 
            },
            scales: {
                x: { 
                    title: { display: true, text: 'ISO-8601 epidemiological week', font: {size: 10} },
                    ticks: { font: { size: 9 }, maxTicksLimit: 25 },
                    grid: { drawOnChartArea: true, color: '#f1f5f9', borderDash: [2, 2] }
                },
                y: { 
                    title: { display: true, text: 'Reported case count', font: {size: 10} },
                    beginAtZero: true, 
                    ticks: { font: { size: 10 } },
                    grid: { drawOnChartArea: true, color: '#f1f5f9', borderDash: [2, 2] }
                }
            }
        }
    });
}

async function updateCorrelationAnalysis() {
    const panel = document.getElementById('correlation-analysis-panel');
    if (!panel || panel.style.display === 'none') return;
    
    const features = getFilteredFeatures();
    if (features.length < 5) {
        document.getElementById('correlation-summary-text').innerText = "Not enough data points for spatial clustering.";
        if (correlationAnalysisChart) correlationAnalysisChart.destroy();
        return;
    }
    
    document.getElementById('correlation-summary-text').innerHTML = "<i class='spinner-border spinner-border-sm me-2'></i> Querying PostGIS for clusters...";
    
    // Extract context for the backend API
    const pointsData = features.map(f => ({
        lon: f.geometry.coordinates[0],
        lat: f.geometry.coordinates[1],
        date: f.properties.date_of_onset || f.properties.date_reported,
        disease: f.properties.disease_type
    }));
    
    try {
        const response = await fetch('/api/spatial-clustering/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ 
                points: pointsData,
                diseases: visibleDiseases 
            })
        });
        
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        
        const clusteredCount = data.clustered_count;
        const noiseCount = data.noise_count;
        const clusterIdsSize = data.num_clusters;
        const clusterPercentage = data.cluster_percentage;
        
        let inference = "";
        if (clusterPercentage > 50) {
            inference = `<span class="text-danger fw-bold"><i class="bi bi-exclamation-triangle"></i> Strong spatial clustering (${clusterPercentage}% of cases in ${clusterIdsSize} hotspots).</span> Potential localized outbreaks detected.`;
        } else if (clusterPercentage > 20) {
            inference = `<span class="text-warning fw-bold">Moderate spatial clustering (${clusterPercentage}% of cases).</span> Small distinct clusters detected.`;
        } else {
            inference = `<span class="text-success fw-bold">Cases are randomly distributed (${clusterPercentage}% in clusters).</span> No significant geographic hotspots detected within 5km radius.`;
        }
        
        document.getElementById('correlation-summary-text').innerHTML = inference;
        
        const ctx = document.getElementById('correlationChart').getContext('2d');
        if (correlationAnalysisChart) correlationAnalysisChart.destroy();
        
        correlationAnalysisChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Clustered Cases', 'Random/Noise Cases'],
                datasets: [{
                    data: [clusteredCount, noiseCount],
                    backgroundColor: ['#ef4444', '#cbd5e1'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: { 
                    legend: { position: 'right', labels: { boxWidth: 12, font: {size: 11} } }
                }
            }
        });
    } catch (err) {
        document.getElementById('correlation-summary-text').innerHTML = `<span class="text-danger">Failed to calculate spatial clustering: ${err.message}</span>`;
        if (correlationAnalysisChart) correlationAnalysisChart.destroy();
    }
}

window.downloadChart = function(canvasId, filename) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    // Create a temporary canvas to draw with a white background
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    const ctx = tempCanvas.getContext('2d');
    
    // Fill white background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
    
    // Draw original canvas over it
    ctx.drawImage(canvas, 0, 0);
    
    const link = document.createElement('a');
    link.download = filename;
    link.href = tempCanvas.toDataURL('image/png');
    link.click();
};
