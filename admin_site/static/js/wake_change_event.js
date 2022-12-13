const WAKE_PLAN_FROM_URL_KEY = "last_plan_id"

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

function ReturnToLastVisitedWakePlan() {

  sessionStorage.setItem(
    'going_back_to_wake_plan',
    'true')

  location.assign(
    sessionStorage.getItem(WAKE_PLAN_FROM_URL_KEY)
    )
}
