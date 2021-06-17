// Properties

let current_id = null,
    local_scripts = [],
    state = {
        query: '',    
        filtered_local_scripts: []
    }

// DOM elements

const search_form_el = document.getElementById('search_form')
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
    saveState(state)
}

const saveState = function(data) {
    sessionStorage.setItem('os2borgerpcscriptsearch', JSON.stringify(data))
}

const loadState = function() {
    const data = sessionStorage.getItem('os2borgerpcscriptsearch')
    if (data) {
        return JSON.parse(data)
    } else {
        return state
    }   
}

const showAllOrSome = function(state) {
    if (state.filtered_local_scripts.length > 0) {
        renderList(list_el, state.filtered_local_scripts)
    } else {
        renderList(list_el, local_scripts)
    }
}

const initialize = function(state) {
    if (state.query) {
        search_form_el.value = state.query
    }
    showAllOrSome(state)
}

// Event listeners

search_form_el.addEventListener('input', function(ev) {
    state.query = this.value
    if (state.query !== '') {
        script_nav_el.style.display = 'none'
        search_result_el.style.display = 'block'
        state.filtered_local_scripts = local_scripts.filter(script => {
            return script.name.includes(state.query)
        })
        showAllOrSome(state)
    } else {
        search_result_el.style.display = 'none'
        script_nav_el.style.display = 'block'
    }
})

window.addEventListener('load', function() {
    state = loadState()
    initialize(state)
})
