const week_plan = document.getElementById("week-plan")

function week_day_on(el, on) {
  const start_time = el.parentElement.parentElement.children[2]
  const separator = el.parentElement.parentElement.children[3]
  const end_time = el.parentElement.parentElement.children[4]
  const on_off_text = el.parentElement.lastElementChild

  if (on) {
    start_time.style.visibility = "visible"
    separator.style.visibility = "visible"
    end_time.style.visibility = "visible"
    on_off_text.innerText = "Tændt"
  }
  else {
    start_time.style.visibility = "hidden"
    separator.style.visibility = "hidden"
    end_time.style.visibility = "hidden"
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

// By default all dates are seen as "on" - this toggles those off to off
for (let day of week_plan.tBodies[0].children) {
  const checkbox = day.getElementsByClassName('checkbox')[0]
  if (! checkbox.checked) {
    week_day_on(checkbox, false)
  }
}
