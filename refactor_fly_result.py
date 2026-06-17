with open('C:/Users/user/infectious_diseases_mapping/surveillance/static/js/map_logic.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """        // Try to match search result with Province or District dropdowns
        let matched = false;
        const provSelect = document.getElementById('province-select');
        const distSelect = document.getElementById('district-select');
        
        if (provSelect) {
            for (let i = 0; i < provSelect.options.length; i++) {
                if (provSelect.options[i].text.toLowerCase() === label.toLowerCase()) {
                    $(provSelect).val(provSelect.options[i].value).trigger('change.select2');
                    // Manually trigger the select event since change.select2 doesn't always trigger it for listeners
                    $(provSelect).trigger({ type: 'select2:select' });
                    matched = true;
                    break;
                }
            }
        }
        
        if (!matched && distSelect) {
            for (let i = 0; i < distSelect.options.length; i++) {
                if (distSelect.options[i].text.toLowerCase() === label.toLowerCase()) {
                    $(distSelect).val(distSelect.options[i].value).trigger('change.select2');
                    $(distSelect).trigger({ type: 'select2:select' });
                    matched = true;
                    break;
                }
            }
        }"""

new_code = """        // Match region bounds
        if (window.applyRegionFilter) {
            window.applyRegionFilter(label);
        }"""

content = content.replace(old_code, new_code)

with open('C:/Users/user/infectious_diseases_mapping/surveillance/static/js/map_logic.js', 'w', encoding='utf-8') as f:
    f.write(content)
