with open('C:/Users/user/infectious_diseases_mapping/surveillance/static/js/map_logic.js', 'r', encoding='utf-8') as f:
    content = f.read()

index_code = """
            populateBoundaryDropdowns();

            // --- BUILD REGION INDEX ---
            window.regionIndex = [];
            const provinces = [];
            const districts = [];

            window.boundaryLayer.eachLayer(layer => {
                const props = layer.feature.properties;
                if (!props || !props.name) return;
                
                const level = (props.level || 'district').toLowerCase();
                const rawName = String(props.name);
                let normName = rawName.toLowerCase().replace(/\\s+/g, ' ').trim();
                normName = normName.replace(/\\s+province$/, ''); // normalize province names

                const entry = {
                    normalisedName: normName,
                    originalName: rawName,
                    level: level,
                    feature: layer.feature,
                    bounds: layer.getBounds(),
                    layer: layer,
                    id: String(props.id || props.code || '')
                };

                window.regionIndex.push(entry);
                if (level === 'province') {
                    provinces.push(entry);
                } else {
                    districts.push(entry);
                }
            });

            // Link districts to parent provinces using point-in-polygon
            districts.forEach(dist => {
                try {
                    const center = turf.centerOfMass(dist.feature);
                    for (const prov of provinces) {
                        if (turf.booleanPointInPolygon(center, prov.feature)) {
                            dist.parentProvince = prov;
                            break;
                        }
                    }
                } catch(e) {}
            });
            // --------------------------
"""
content = content.replace("            populateBoundaryDropdowns();", index_code, 1)

apply_filter_code = """
// unified region filter method
window.applyRegionFilter = function(searchString, skipDropdownUpdate = false) {
    if (!window.regionIndex || window.regionIndex.length === 0) return;

    if (!searchString || searchString.trim() === '' || searchString.toLowerCase() === 'all zimbabwe') {
        window.activeRegionPolygon = null;
        window.boundaryLayer.eachLayer(layer => {
            if (!mapInstance.hasLayer(layer)) mapInstance.addLayer(layer);
            window.boundaryLayer.resetStyle(layer);
        });
        mapInstance.flyTo([-19.0154, 29.1549], 6, {duration: 1.5});
        renderCases();
        if (!skipDropdownUpdate) {
            $('#province-select').val('').trigger('change.select2');
            $('#district-select').val('').trigger('change.select2');
        }
        return;
    }

    let normSearch = String(searchString).toLowerCase().replace(/\\s+/g, ' ').trim();
    normSearch = normSearch.replace(/\\s+province$/, '');

    let matchedRegion = window.regionIndex.find(r => r.id === searchString);
    if (!matchedRegion) {
        matchedRegion = window.regionIndex.find(r => r.normalisedName === normSearch || r.originalName.toLowerCase() === normSearch);
    }
    
    if (!matchedRegion) {
        matchedRegion = window.regionIndex.find(r => r.normalisedName.includes(normSearch));
    }

    if (!matchedRegion) {
        const fb = document.getElementById('region-search-input');
        if (fb) {
            const origColor = fb.style.borderColor;
            const origPlace = fb.placeholder;
            fb.style.borderColor = 'red';
            fb.placeholder = 'Region not found';
            fb.value = '';
            setTimeout(() => {
                fb.style.borderColor = origColor;
                fb.placeholder = origPlace;
            }, 2000);
        }
        return;
    }

    if (matchedRegion.bounds.isValid()) {
        mapInstance.flyToBounds(matchedRegion.bounds, {padding: [40, 40], maxZoom: 10, duration: 1.5});
    }

    window.boundaryLayer.eachLayer(layer => {
        let show = false;
        
        if (matchedRegion.level === 'province') {
            if (layer === matchedRegion.layer) show = true;
            else {
                const districtEntry = window.regionIndex.find(r => r.layer === layer);
                if (districtEntry && districtEntry.parentProvince === matchedRegion) {
                    show = true;
                }
            }
        } else {
            if (layer === matchedRegion.layer) show = true;
        }

        if (show) {
            if (!mapInstance.hasLayer(layer)) mapInstance.addLayer(layer);
            if (layer === matchedRegion.layer) {
                layer.setStyle({weight: 3, color: '#ffc107', fillOpacity: 0.1});
            } else {
                window.boundaryLayer.resetStyle(layer);
            }
        } else {
            if (mapInstance.hasLayer(layer)) mapInstance.removeLayer(layer);
        }
    });

    window.activeRegionPolygon = matchedRegion.feature;
    renderCases();

    if (!skipDropdownUpdate) {
        if (matchedRegion.level === 'province') {
            $('#province-select').val(matchedRegion.id).trigger('change.select2');
            $('#district-select').val('').trigger('change.select2');
        } else {
            if (matchedRegion.parentProvince) {
                $('#province-select').val(matchedRegion.parentProvince.id).trigger('change.select2');
            }
            $('#district-select').val(matchedRegion.id).trigger('change.select2');
        }
    }
};

function filterBoundaryLayer(provId, distId) {
    if (distId) {
        window.applyRegionFilter(distId, true);
    } else if (provId) {
        window.applyRegionFilter(provId, true);
    } else {
        window.applyRegionFilter('', true);
    }
}
"""

start_str = "function filterBoundaryLayer(provId, distId) {"
end_str = "// Interactive Data Table View"
start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + apply_filter_code + '\n' + content[end_idx:]


search_orig = "searchInput.addEventListener('keydown', function(e) {\n        if (e.key === 'Enter') {\n            e.preventDefault();\n            const q = searchInput.value.trim();\n            if (!q) return;\n\n            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&countrycodes=zw&limit=5`)"

search_new = """searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const q = searchInput.value.trim();
            if (!q) return;

            const normSearch = q.toLowerCase().replace(/\\s+/g, ' ').trim().replace(/\\s+province$/, '');
            const matchedRegion = window.regionIndex && window.regionIndex.find(r => 
                r.normalisedName === normSearch || 
                r.originalName.toLowerCase() === normSearch ||
                r.normalisedName.includes(normSearch)
            );

            if (matchedRegion) {
                window.applyRegionFilter(q);
                return;
            }

            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&countrycodes=zw&limit=5`)"""

content = content.replace(search_orig, search_new)

with open('C:/Users/user/infectious_diseases_mapping/surveillance/static/js/map_logic.js', 'w', encoding='utf-8') as f:
    f.write(content)
