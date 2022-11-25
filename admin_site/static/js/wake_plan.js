const week_plan = document.getElementById("week-plan")
const wake_change_events = document.getElementById("wake-change-events")
const week_plan_offset = 0
const wake_change_events_offset = 2

function week_day_on(el, on) {

  const start_time = el.parentElement.parentElement.children[3]
  const start_time_input = el.parentElement.parentElement.children[3].firstElementChild
  const separator = el.parentElement.parentElement.children[4]
  const end_time = el.parentElement.parentElement.children[5]
  const end_time_input = el.parentElement.parentElement.children[5].firstElementChild
  const on_off_text = el.parentElement.parentElement.children[2].firstElementChild

  if (on) {
    start_time.style.visibility = "visible"
    start_time_input.setAttribute('required',true)
    separator.style.visibility = "visible"
    end_time.style.visibility = "visible"
    end_time_input.setAttribute('required',true)
    on_off_text.innerText = "Tændt"

  }
  else {
    start_time.style.visibility = "hidden"
    start_time_input.removeAttribute('required')
    separator.style.visibility = "hidden"
    end_time.style.visibility = "hidden"
    end_time_input.removeAttribute('required')
    on_off_text.innerText = "Slukket"
  }
}

// Handling the week plan switches
// Den her håndterer da også undtagelsernes switches/toggles
function checkbox_open_close_handler(event) {
  const tg = event.target

  if (tg.type == "checkbox") {

    if (tg.checked) {
      week_day_on(tg, true)
    }
    else if (!tg.checked) {
      week_day_on(tg, false)
    }
  }
}

// Week plan page specific
if (week_plan) {
  week_plan.addEventListener("click", checkbox_open_close_handler)

  // By default all dates are seen as "on" - this toggles those off to off for the week plan
  for (let day of week_plan.tBodies[0].children) {
    const checkbox = day.getElementsByClassName('checkbox')[0]
    if (! checkbox.checked) {
      week_day_on(checkbox, false)
    }
    else {
      week_day_on(checkbox, true)
    }
  }
}

const checkbox_enabled = document.getElementById("id_enabled")
const checkbox_enabled_label = document.getElementById("id_enabled_label")
if (checkbox_enabled) { // Don't attempt to set this listener if we're on a subpage where this doesn't exist
  function set_plan_state_text(on) {
    if (on) {
      checkbox_enabled_label.innerText = "Aktiv"
    }
    else checkbox_enabled_label.innerText = "Inaktiv"
  }

  checkbox_enabled.addEventListener('click', function() {
    if (checkbox_enabled.checked) set_plan_state_text(true)
    else set_plan_state_text(false)
  })
}

// Wake change event specific
if (document.getElementById("wake-change-plan")) {

  // Set all times required for altered hours wake change events
  const times = document.getElementsByClassName("wake-change-event-time")
  for (let time of times) {
    time.firstElementChild.setAttribute('required',true)
  }

  // Set the end date to the start date by default, if end date is empty, to make it faster to make intervals and
  // especially individual days
  const start_el = document.getElementById("id_date_start")
  const end_el = document.getElementById("id_date_end")

  if (start_el) {
    start_el.addEventListener('change', function() {
      if (end_el.value == "") {
        end_el.value = start_el.value
      }
    })
  }
}

// TODO: If a new wakechangeevent is saved, set a cookie with its ID and name, and then this page could have a focus listener that add it to the picklist as an option?
// Activate the info button popover
$(document).ready(function(){
  $('[data-toggle="popover"]').popover();
});
