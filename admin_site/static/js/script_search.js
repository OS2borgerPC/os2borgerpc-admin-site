// Properties

let current_id = null,
    local_scripts = [],
    state = {
        query: '',    
        filtered_local_scripts: []
    }

// DOM elements

const search_form_el = document.getElementById('search_form')
const search_clear_el = document.getElementById('search-clear-btn')
const script_nav_el = document.getElementById('script-navigation')
const search_result_el = document.getElementById('script-searchlist')
const list_el = document.getElementById('script-search-list')

// Methods

const renderList = function (list_el, script_list) {
    list_el.innerHTML = ''
    for (let s of script_list) {
        let item = document.createElement('li')
        let template = `
            <a class="item-list-link" href="${ s.url }">
                ${ s.name }
            </a>
        `
        if (s.id === current_id) {
            item.className = 'active'
            template += `
                <a class="item-list-deletable material-icons" href="${ s.delete_url }" title="Slet script">
                    clear
                </a>
            `
        }
        item.innerHTML = template
        list_el.appendChild(item)
    }
}

const showNoneOrSome = function(state) {
    if (state.query !== '') {
        script_nav_el.style.display = 'none'
        search_result_el.style.display = 'block'
        renderList(list_el, state.filtered_local_scripts)
    } else {
        search_result_el.style.display = 'none'
        script_nav_el.style.display = 'block'
        renderList(list_el, local_scripts)
    }
}

// Event listeners

// React on search input
search_form_el.addEventListener('input', function(ev) {
    state.query = this.value.toLowerCase()
    state.filtered_local_scripts = local_scripts.filter(script => {
        return script.name.toLowerCase().includes(state.query)
    })
    showNoneOrSome(state)
})

// When clicking the search input "clear" button, reset the input
search_clear_el.addEventListener('click', function(ev) {
    search_form_el.value = ''
    state.query = ''
    showNoneOrSome(state)
})
