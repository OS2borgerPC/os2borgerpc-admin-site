const WEEK_PLAN = document.getElementById("week-plan")
const WAKE_PLAN_FROM_URL_KEY = "last_plan_id"
const LANGUAGE = getCookie("django_language")

// Turns a week day on/off
// If off start_time and end_time are hidden. If on required is set to true, to remove the browser x button to clear the time field
function weekDayOn(el, on) {

  const START_TIME = el.parentElement.parentElement.children[3]
  const START_TIME_INPUT = el.parentElement.parentElement.children[3].firstElementChild
  const SEPARATOR = el.parentElement.parentElement.children[4]
  const END_TIME = el.parentElement.parentElement.children[5]
  const END_TIME_INPUT = el.parentElement.parentElement.children[5].firstElementChild
  const ON_OFF_TEXT = el.parentElement.parentElement.children[2].firstElementChild

  // Dict containing the translations for the switch
  var text_dict = {
      "da": ["Tændt", "Slukket"],
      "en": ["On", "Off"],
      "sv": ["På", "Stängd"]
  }

  // Get the correct translation based on the django_language cookie
    const text = text_dict[LANGUAGE]

  if (on) {
    START_TIME.style.visibility = "visible"
    START_TIME_INPUT.setAttribute('required',true)
    SEPARATOR.style.visibility = "visible"
    END_TIME.style.visibility = "visible"
    END_TIME_INPUT.setAttribute('required',true)
    // TODO: Use django JS translations instead
    ON_OFF_TEXT.innerText = text[0]
    //ON_OFF_TEXT.innerText = gettext("On")

  }
  else {
    START_TIME.style.visibility = "hidden"
    START_TIME_INPUT.removeAttribute('required')
    SEPARATOR.style.visibility = "hidden"
    END_TIME.style.visibility = "hidden"
    END_TIME_INPUT.removeAttribute('required')
    // TODO: Use django JS translations instead
    ON_OFF_TEXT.innerText = text[1]
    //ON_OFF_TEXT.innerText = gettext("Off")
  }
}

// Handling the week plan switches
function checkboxOpenCloseHandler(event) {
  const TG = event.target

  if (TG.type == "checkbox") {

    if (TG.checked) {
      weekDayOn(TG, true)
    }
    else if (!TG.checked) {
      weekDayOn(TG, false)
    }
  }
}

WEEK_PLAN.addEventListener("click", checkboxOpenCloseHandler)

// By default all dates are seen as "on" - this toggles those off to off for the week plan
for (let day of WEEK_PLAN.tBodies[0].children) {
  const checkbox = day.getElementsByClassName('checkbox')[0]
  if (! checkbox.checked) {
    weekDayOn(checkbox, false)
  }
  else {
    weekDayOn(checkbox, true)
  }
}

const CHECKBOX_ENABLED = document.getElementById("id_enabled")
const CHECKBOX_ENABLED_LABEL = document.getElementById("id_enabled_label")
if (CHECKBOX_ENABLED) { // Don't attempt to set this listener if we're on a subpage where this doesn't exist
  function setPlanStateText(on) {
    // TODO: Use django JS translations instead
    // Dict containing the translations for the switch
    var text_dict = {
        "da": ["Aktiv", "Inaktiv"],
        "en": ["Active", "Inactive"],
        "sv": ["Aktiv", "Inaktiv"]
    }

    // Get the correct translation based on the django_language cookie
    const text = text_dict[LANGUAGE]

    if (on) {
      CHECKBOX_ENABLED_LABEL.innerText = text[0]
      // CHECKBOX_ENABLED_LABEL.innerText = gettext("Active")
    }
    else CHECKBOX_ENABLED_LABEL.innerText = text[1]
    // else CHECKBOX_ENABLED_LABEL.innerText = gettext("Inactive")
  }

  CHECKBOX_ENABLED.addEventListener('click', function() {
    if (CHECKBOX_ENABLED.checked) setPlanStateText(true)
    else setPlanStateText(false)
  })
}

// TODO: If a new wakechangeevent is saved, set a cookie with its ID and name, and then this page could have a focus listener that add it to the picklist as an option?

// Store current plan_id in SessionStorage
sessionStorage.setItem(
  WAKE_PLAN_FROM_URL_KEY,
  $(location).attr('href')
)

// Store the state of the wake plan if clicking any of the wake change events buttons (except the picklist which isn't handled here)
$("#custom-wake-plans").click(function(){
  saveInputStates()
});

// Serialize current wake plan, save it to session storage
function saveInputStates() {
  sessionStorage.setItem(
    'wake_plan_settings',
    JSON.stringify(getWakePlanSettingsAsJSON())
    )
  sessionStorage.setItem('going_to_wake_change_events','true')
}

// Serialise the current week plan state to JSON (relevant if there are unsaved changes), done before saving it to session storage
// This does not handle saving the picklists
function getWakePlanSettingsAsJSON() {
  const wakePlanSettingsAsJSON = {}
  wakePlanSettingsAsJSON.activated = document.getElementById('id_enabled').checked
  wakePlanSettingsAsJSON.activated_label = document.getElementById('id_enabled_label').textContent
  wakePlanSettingsAsJSON.name = document.getElementById('id_name').value
  wakePlanSettingsAsJSON.sleep_state = document.getElementById('id_sleep_state').value
  wakePlanSettingsAsJSON.monday_open = document.getElementById('id_monday_open').checked
  wakePlanSettingsAsJSON.monday_on = document.getElementById('id_monday_on').value
  wakePlanSettingsAsJSON.monday_off = document.getElementById('id_monday_off').value
  wakePlanSettingsAsJSON.tuesday_open = document.getElementById('id_tuesday_open').checked
  wakePlanSettingsAsJSON.tuesday_on = document.getElementById('id_tuesday_on').value
  wakePlanSettingsAsJSON.tuesday_off = document.getElementById('id_tuesday_off').value
  wakePlanSettingsAsJSON.wednesday_open = document.getElementById('id_wednesday_open').checked
  wakePlanSettingsAsJSON.wednesday_on = document.getElementById('id_wednesday_on').value
  wakePlanSettingsAsJSON.wednesday_off = document.getElementById('id_wednesday_off').value
  wakePlanSettingsAsJSON.thursday_open = document.getElementById('id_thursday_open').checked
  wakePlanSettingsAsJSON.thursday_on = document.getElementById('id_thursday_on').value
  wakePlanSettingsAsJSON.thursday_off = document.getElementById('id_thursday_off').value
  wakePlanSettingsAsJSON.friday_open = document.getElementById('id_friday_open').checked
  wakePlanSettingsAsJSON.friday_on = document.getElementById('id_friday_on').value
  wakePlanSettingsAsJSON.friday_off = document.getElementById('id_friday_off').value
  wakePlanSettingsAsJSON.saturday_open = document.getElementById('id_saturday_open').checked
  wakePlanSettingsAsJSON.saturday_on = document.getElementById('id_saturday_on').value
  wakePlanSettingsAsJSON.saturday_off = document.getElementById('id_saturday_off').value
  wakePlanSettingsAsJSON.sunday_open = document.getElementById('id_sunday_open').checked
  wakePlanSettingsAsJSON.sunday_on = document.getElementById('id_sunday_on').value
  wakePlanSettingsAsJSON.sunday_off = document.getElementById('id_sunday_off').value

  return wakePlanSettingsAsJSON
}

// Restore a wake plan after returning from wake change event
function runWhenReturnedToPage() {

  const wakePlanSettingsAsJSON = JSON.parse(sessionStorage.getItem('wake_plan_settings'))

  document.getElementById('id_enabled').checked = wakePlanSettingsAsJSON.activated
  document.getElementById('id_enabled_label').textContent = wakePlanSettingsAsJSON.activated_label
  document.getElementById('id_name').value = wakePlanSettingsAsJSON.name
  document.getElementById('id_sleep_state').value = wakePlanSettingsAsJSON.sleep_state
  document.getElementById('id_monday_open').checked = wakePlanSettingsAsJSON.monday_open
  weekDayOn(document.getElementById('id_monday_open'), wakePlanSettingsAsJSON.monday_open)
  document.getElementById('id_monday_on').value = wakePlanSettingsAsJSON.monday_on
  document.getElementById('id_monday_off').value = wakePlanSettingsAsJSON.monday_off
  document.getElementById('id_tuesday_open').checked = wakePlanSettingsAsJSON.tuesday_open
  weekDayOn(document.getElementById('id_tuesday_open'), wakePlanSettingsAsJSON.tuesday_open)
  document.getElementById('id_tuesday_on').value = wakePlanSettingsAsJSON.tuesday_on
  document.getElementById('id_tuesday_off').value = wakePlanSettingsAsJSON.tuesday_off
  document.getElementById('id_wednesday_open').checked = wakePlanSettingsAsJSON.wednesday_open
  weekDayOn(document.getElementById('id_wednesday_open'), wakePlanSettingsAsJSON.wednesday_open)
  document.getElementById('id_wednesday_on').value = wakePlanSettingsAsJSON.wednesday_on
  document.getElementById('id_wednesday_off').value = wakePlanSettingsAsJSON.wednesday_off
  document.getElementById('id_thursday_open').checked = wakePlanSettingsAsJSON.thursday_open
  weekDayOn(document.getElementById('id_thursday_open'), wakePlanSettingsAsJSON.thursday_open)
  document.getElementById('id_thursday_on').value = wakePlanSettingsAsJSON.thursday_on
  document.getElementById('id_thursday_off').value = wakePlanSettingsAsJSON.thursday_off
  document.getElementById('id_friday_open').checked = wakePlanSettingsAsJSON.friday_open
  weekDayOn(document.getElementById('id_friday_open'), wakePlanSettingsAsJSON.friday_open)
  document.getElementById('id_friday_on').value = wakePlanSettingsAsJSON.friday_on
  document.getElementById('id_friday_off').value = wakePlanSettingsAsJSON.friday_off
  document.getElementById('id_saturday_open').checked = wakePlanSettingsAsJSON.saturday_open
  weekDayOn(document.getElementById('id_saturday_open'), wakePlanSettingsAsJSON.saturday_open)
  document.getElementById('id_saturday_on').value = wakePlanSettingsAsJSON.saturday_on
  document.getElementById('id_saturday_off').value = wakePlanSettingsAsJSON.saturday_off
  document.getElementById('id_sunday_open').checked = wakePlanSettingsAsJSON.sunday_open
  weekDayOn(document.getElementById('id_sunday_open'), wakePlanSettingsAsJSON.sunday_open)
  document.getElementById('id_sunday_on').value = wakePlanSettingsAsJSON.sunday_on
  document.getElementById('id_sunday_off').value = wakePlanSettingsAsJSON.sunday_off
}


// ???
let going_back_to_wake_plan_string = sessionStorage.getItem('going_back_to_wake_plan')

let going_back_to_wake_plan_boolean = going_back_to_wake_plan_string === 'true'

// When returning to the wake plan restore the state and ...?
if (going_back_to_wake_plan_boolean) {
  sessionStorage.setItem('going_back_to_wake_plan','false')
  runWhenReturnedToPage()
}

sessionStorage.setItem('going_to_wake_change_events','false')

// When a link is clicked in the wake_change_event picklist it must save the wake plan state
addEventListener('click', evt => {
  let classString = evt.target.getAttribute("class")
  if (!(classString === null)) {
    let wake_change_events_link_clicked = classString.includes('wake_change_events_link')
    if (wake_change_events_link_clicked) {
      saveInputStates()
    }
  }
})


// ???
addEventListener('beforeunload', evt => {
  let going_to_wake_change_events_string = sessionStorage.getItem('going_to_wake_change_events')

  let going_to_wake_change_events_boolean = going_to_wake_change_events_string === 'true'

  if (!(going_to_wake_change_events_boolean)) {
    removeDataFromSessionStorage()
  }
});


// When pressing F5 please clear the stored wake plan
// Even with reload it remembers the toggle switches settings state even though it should be reset to what it is from the database
// Another limitation is that the user can refresh with Ctrl-f5 or pressing the button to refresh
// TODO: fix the above
addEventListener('keydown', evt => {
  if (evt.key === 'F5') {
    removeDataFromSessionStorage()
    location.reload(true)
  }
})

// A function to clear the session storage storing what a wake plan looks like to be able to navigate to wake
// change events from a wake plan without losing wake plan state
function removeDataFromSessionStorage() {

  sessionStorage.setItem('going_to_wake_change_events', 'false')

  sessionStorage.setItem('going_back_to_wake_plan', 'false')

  sessionStorage.setItem('wake_plan_settings', '{}')

  sessionStorage.setItem(
    'wake_plan_wake_change_events_user_has_made_changes_to_options',
    'false')
  sessionStorage.setItem('wake_plan_wake_change_events_options', '[]')

  sessionStorage.setItem(
    'wake_plan_groups_user_has_made_changes_to_options',
    'false')
  sessionStorage.setItem('wake_plan_groups_options', '[]')
}

document.getElementById('submit-button').addEventListener("click", function(event){
  removeDataFromSessionStorage()
});

document.getElementById('cancel-button').addEventListener("click", function(event){
  removeDataFromSessionStorage()
  location.reload(true) // true means it reloads from server, false will reload from cache
});

// Limitation: Doesn't currently detect changes in picklists! Also it prevents "Gem ændringer" and going to Wake Change Events, which isn't great
// TODO is considering whether this should be added, in some edited form, to all pages in the future, fx. by adding it to custom.js
// Credit: https://stackoverflow.com/a/57069660
// 'use strict'
// (() => {
//   const modified_inputs = new Set()
//   const defaultValue = 'defaultValue'
//   // store default values
//   addEventListener('beforeinput', evt => {
//     const target = evt.target
//     if (!(defaultValue in target.dataset)) {
//       target.dataset[defaultValue] = ('' + (target.value || target.textContent)).trim()
//     }
//   })
//
//   // detect input modifications
//   addEventListener('input', evt => {
//     const target = evt.target
//     let original = target.dataset[defaultValue]
//
//     let current = ('' + (target.value || target.textContent)).trim()
//
//     if (original !== current) {
//       if (!modified_inputs.has(target)) {
//         modified_inputs.add(target)
//       }
//     } else if (modified_inputs.has(target)) {
//       modified_inputs.delete(target)
//     }
//   })
//
//   addEventListener(
//     'saved',
//     function(e) {
//       modified_inputs.clear()
//     },
//     false
//   )
//
//   addEventListener('beforeunload', evt => {
//     if (modified_inputs.size) {
//       const unsaved_changes_warning = 'Ændringer du har lavet er ikke blevet gemt.'
//       evt.returnValue = unsaved_changes_warning
//       return unsaved_changes_warning
//     }
//   })
//
// })()
//
// document.getElementById('submit-button').addEventListener("click", function(event){
//   removeDataFromSessionStorage()
// })
//
// document.getElementById('cancel-button').addEventListener("click", function(event){
//   removeDataFromSessionStorage()
//   location.reload(true) // true means it reloads from server, false will reload from cache
// })
