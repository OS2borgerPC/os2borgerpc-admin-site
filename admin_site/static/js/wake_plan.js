const week_plan = document.getElementById("week-plan")
const wake_change_events = document.getElementById("wake-change-events")
const week_plan_offset = 0
const wake_change_events_offset = 2

function week_day_on(el, on, wake_change_event=false) {
  const offset = wake_change_event? wake_change_events_offset : 0

  const start_time = el.parentElement.parentElement.children[3 + offset]
  const start_time_input = el.parentElement.parentElement.children[3 + offset].firstElementChild
  const separator = el.parentElement.parentElement.children[4 + offset]
  const end_time = el.parentElement.parentElement.children[5 + offset]
  const end_time_input = el.parentElement.parentElement.children[5 + offset].firstElementChild
  const on_off_text = el.parentElement.parentElement.children[2 + offset].firstElementChild

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
    start_time_input.setAttribute('required',false)
    separator.style.visibility = "hidden"
    end_time.style.visibility = "hidden"
    end_time_input.setAttribute('required',false)
    on_off_text.innerText = "Slukket"
  }
}

// Handling the week plan switches
function handle_click(event) {
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

week_plan.addEventListener("click", handle_click)
wake_change_events.addEventListener("click", handle_click)

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

// Do the same for events
for (let event of wake_change_events.tBodies[0].children) {
  const checkbox = event.getElementsByClassName('checkbox')[0]
  if (! checkbox.checked) {
    // TODO: This doesn't work currently:
    week_day_on(checkbox, false, true)
  }
  else {
    week_day_on(checkbox, true, true)
  }
}
