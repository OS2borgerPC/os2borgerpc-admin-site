const WEEK_PLAN = document.getElementById("week-plan")
const WAKE_PLAN_FROM_URL_KEY = "last_plan_id"

function weekDayOn(el, on) {

  const START_TIME = el.parentElement.parentElement.children[3]
  const START_TIME_INPUT = el.parentElement.parentElement.children[3].firstElementChild
  const SEPARATOR = el.parentElement.parentElement.children[4]
  const END_TIME = el.parentElement.parentElement.children[5]
  const END_TIME_INPUT = el.parentElement.parentElement.children[5].firstElementChild
  const ON_OFF_TEXT = el.parentElement.parentElement.children[2].firstElementChild

  if (on) {
    START_TIME.style.visibility = "visible"
    START_TIME_INPUT.setAttribute('required',true)
    SEPARATOR.style.visibility = "visible"
    END_TIME.style.visibility = "visible"
    END_TIME_INPUT.setAttribute('required',true)
    ON_OFF_TEXT.innerText = "Tændt"

  }
  else {
    START_TIME.style.visibility = "hidden"
    START_TIME_INPUT.removeAttribute('required')
    SEPARATOR.style.visibility = "hidden"
    END_TIME.style.visibility = "hidden"
    END_TIME_INPUT.removeAttribute('required')
    ON_OFF_TEXT.innerText = "Slukket"
  }
}

// Handling the week plan switches
// Den her håndterer da også undtagelsernes switches/toggles
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

// Week plan page specific
if (WEEK_PLAN) {
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
}

const CHECKBOX_ENABLED = document.getElementById("id_enabled")
const CHECKBOX_ENABLED_LABEL = document.getElementById("id_enabled_label")
if (CHECKBOX_ENABLED) { // Don't attempt to set this listener if we're on a subpage where this doesn't exist
  function setPlanStateText(on) {
    if (on) {
      CHECKBOX_ENABLED_LABEL.innerText = "Aktiv"
    }
    else CHECKBOX_ENABLED_LABEL.innerText = "Inaktiv"
  }

  CHECKBOX_ENABLED.addEventListener('click', function() {
    if (CHECKBOX_ENABLED.checked) setPlanStateText(true)
    else setPlanStateText(false)
  })
}

// Wake change event specific
if (document.getElementById("wake-change-plan")) {

  // Set all TIMES required for altered hours wake change events
  const TIMES = document.getElementsByClassName("wake-change-event-time")
  for (let time of TIMES) {
    time.firstElementChild.setAttribute('required',true)
  }

  // Set the end date to the start date by default, if end date is empty, to make it faster to make intervals and
  // especially individual days
  const START_EL = document.getElementById("id_date_start")
  const END_EL = document.getElementById("id_date_end")

  if (START_EL) {
    START_EL.addEventListener('change', function() {
      if (END_EL.value == "") {
        END_EL.value = START_EL.value
      }
    })
  }
}

// TODO: If a new wakechangeevent is saved, set a cookie with its ID and name, and then this page could have a focus listener that add it to the picklist as an option?
// Activate the info button popover
$(document).ready(function(){
  $('[data-toggle="popover"]').popover();
});

// Store current plan_id in SessionStorage
$("#custom_wake_plans").click(function(){
  sessionStorage.setItem(
    WAKE_PLAN_FROM_URL_KEY,
    $(location).attr('href')
    )
});

function ReturnToLastVisitedWakePlan() {
  location.assign(
    sessionStorage.getItem(WAKE_PLAN_FROM_URL_KEY)
    )
}


// Credit: https://stackoverflow.com/a/57069660
'use strict';
  (() => {
    const modified_inputs = new Set();
    const defaultValue = 'defaultValue';
    // store default values
    addEventListener('beforeinput', evt => {
      const target = evt.target;
      if (!(defaultValue in target.dataset)) {
        target.dataset[defaultValue] = ('' + (target.value || target.textContent)).trim();
      }
    });

    // detect input modifications
    addEventListener('input', evt => {
      const target = evt.target;
      let original = target.dataset[defaultValue];

      let current = ('' + (target.value || target.textContent)).trim();

      if (original !== current) {
        if (!modified_inputs.has(target)) {
          modified_inputs.add(target);
        }
      } else if (modified_inputs.has(target)) {
        modified_inputs.delete(target);
      }
    });

    addEventListener(
      'saved',
      function(e) {
        modified_inputs.clear()
      },
      false
    );

    addEventListener('beforeunload', evt => {
      if (modified_inputs.size) {
        const unsaved_changes_warning = 'Changes you made may not be saved.';
        evt.returnValue = unsaved_changes_warning;
        return unsaved_changes_warning;
      }
    });

  })();
