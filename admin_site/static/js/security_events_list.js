$(function(){
    var SecurityEventList = function(container_elem, template_container_id) {
        this.elem = $(container_elem)
        this.searchUrl = window.security_event_search_url
        this.updateUrl = window.security_events_update_url
        this.statusSelectors = []
        BibOS.addTemplate('securityevent-entry', template_container_id)
    }
    $.extend(SecurityEventList.prototype, {
        init: function() {
            var securityeventlist = this
            $('#securityeventsearch-status-selectors input:checkbox').on("change", function() {
                securityeventlist.search()
            })
            $('#securityeventsearch-level-selectors input:checkbox').on("change", function() {
                securityeventlist.search()
            })
            securityeventlist.search()

            $('#all_events_toggle').on("change", function() {
                all_events_checked = this.checked
                $("#securityevent-list input:checkbox").each(function() {
                    this.checked = all_events_checked
                    selectEvent(this)
                })
            })

            $('#handle_events_save_button').on("click", function() {
                securityeventlist.handle_events()

                var modal_element = document.getElementById('handle_events_modal')
                var handle_security_events_modal = bootstrap.Modal.getInstance(modal_element)
                handle_security_events_modal.hide()
            })

        },

        appendEntries: function(dataList) {
            var container = this.elem
            $.each(dataList.results, function() {
                const maybe_note = this.note? '<strong>Note sat ved håndtering: </strong><br>' + this.note : ''
                var info_button = '<button ' +
                        'class="btn btn-secondary loginfobutton p-0" ' +
                        'data-bs-title="Info om hændelsen" ' +
                        'data-bs-toggle="popover" ' +
                        'data-bs-content="' + '<strong>Log-output fra hændelsen:</strong><br/><br/><pre class=\'p-3 bg-light\'>' + this.summary + '</pre><br/>' + maybe_note + '"' +
                        'data-bs-html=true ' +
                        'data-bs-placement=left ' +
                        'data-bs-trigger="click" ' +
                        'data-bs-animation="true" ' +
                        'data-pk="' + this.pk + '"' +
                    '><span class="material-icons fs-2">info</span></button>'
                var pc_link = '<a href="' + this.pc_url + '">' + this.pc_name + '</a>'
                var problem_link = '<a href="' + this.problem_url + '">' + this.problem_name + '</a>'
                var assigned_user_link = '<a href="' + this.assigned_user_url + '">' + this.assigned_user + '</a>'
                var item = $(BibOS.expandTemplate(
                    'securityevent-entry',
                    $.extend(this, {
                        'pc_link' : pc_link,
                        'problem_link': problem_link,
                        'assigned_user_link': assigned_user_link,
                        'info_button': info_button,
                    })
                ))
                item.attr('event-id', this.pk)
                item.appendTo(container)
            })
            document.getElementById("all_events_toggle").checked = false
            updateCounter()
            BibOS.setupSecurityEventLogInfoButtons(container)
        },

        replaceEntries: function(dataList) {
            this.elem.find('tr').remove()
            this.appendEntries(dataList)
        },

        selectFilter: function(field, elem, val) {
            var e = $(elem)
            if(e.hasClass('selected')) {
                e.removeClass('selected')
                val = ''
            } else {
                e.parent().find('li').removeClass('selected')
                e.addClass('selected')
            }
            $('#securityeventsearch-filterform input[name=' + field + ']').val(val)
            this.search()
        },

        selectPC: function(elem, val) {
            this.selectFilter('pc', elem, val)
        },

        orderby: function(order) {
            var input = $('#securityeventsearch-filterform input[name=orderby]')
            input.val(BibOS.getOrderBy(input.val(), order))
            this.search()
        },
        setUpPaginationCount: function(data) {
            $("div#pagination-count").text(calcPaginationRange(data, 20))
        },
        setUpPaginationLinks: function(data) {
            var pagination = $("ul.pagination")
            pagination.empty()
            var eventsearch = this

            var previous_item = $('<li class="page-item disabled"><a class="page-link"><span class="material-icons">navigate_before</span> Forrige</a></li>')
            if (data.has_previous) {
                previous_item.removeClass("disabled")
                previous_item.find('a').on("click", function() {
                    var input = $('#securityeventsearch-filterform input[name=page]')
                    input.val(data.previous_page_number)
                    eventsearch.search()
                })
            }
            previous_item.appendTo(pagination)

            data.page_numbers.forEach(function(page) {
                if (data.page == page) {
                    item = $('<li class="page-item active"><a class="page-link">' + page + '</a></li>')
                }
                else {
                    item = $('<li class="page-item"><a class="page-link">' + page + '</a></li>')
                }
                item.find('a').on("click", function() {
                    var input = $('#securityeventsearch-filterform input[name=page]')
                    input.val(page)
                    eventsearch.search()
                })
                item.appendTo(pagination)
            })

            var next_item = $('<li class="page-item disabled"><a class="page-link">Næste <span class="material-icons">navigate_next</span></a></li>')
            if (data.has_next) {
                next_item.removeClass("disabled")
                next_item.find('a').on("click", function() {
                    var input = $('#securityeventsearch-filterform input[name=page]')
                    input.val(data.next_page_number)
                    eventsearch.search()
                })
            }
            next_item.appendTo(pagination)
        },
        search: function() {
            var js = this
            js.searchConditions = $('#securityeventsearch-filterform').serialize()

            $.ajax({
                type: "GET",
                url: js.searchUrl,
                data: js.searchConditions,
                success: function(data) {
                    js.replaceEntries(data)
                    js.setUpPaginationCount(data)
                    js.setUpPaginationLinks(data)
                },
                error: function(err) {
                    console.log(err)
                },
                dataType: "json"
            })
        },
        handle_events: function() {
            var js = this
            event_ids = []
            $("#securityevent-list input:checkbox:checked").each(function() {
                event_ids.push($(this).parents("tr").attr('event-id'))
            })
            status = $("[name='status']").find(":selected").val()
            note = $("[name='note']").val()
            assigned_user = $("[name='assigned_user']").find(":selected").val()

            $.post({
                type: "POST",
                url: js.updateUrl,
                data: $.param({'ids': event_ids, 'status': status, 'note':note, 'assigned_user':assigned_user}, true),
                success: function() {
                    js.search()
                }
            })
        },
        reset: function() {
            $('#securityeventsearch-filterform')[0].reset()
            $('#securityeventsearch-filterform li.selected').removeClass('selected')
            $('#jobsearch-filterform input[name=pc]').val('')
            $('#jobsearch-filterform input[name=page]').val('1')
            this.search()
        }
    })
    BibOS.SecurityEventList = new SecurityEventList('#securityevent-list', '#securityeventitem-template')
    $(function() { BibOS.SecurityEventList.init() })
})

function selectEvent(item) {
    item.closest("tr").classList.toggle("selected", item.checked)
    updateCounter()
}

function updateCounter() {
    selectedEvents = document.getElementsByClassName("selected").length
    totalEvents = document.getElementsByClassName("click-list--item").length - 1
    handleButton = document.getElementById("handle-event-button")

    // Updates the text on the button to show how many (if any) events have been selected
    handleButton.innerText = "Håndter " + ( selectedEvents > 0 ? selectedEvents + " ud af " + totalEvents : "") + " advarsler"

    // Disables the button when no elements are selected
    document.getElementById("handle-event-button").disabled = ( selectedEvents == 0 )
}
