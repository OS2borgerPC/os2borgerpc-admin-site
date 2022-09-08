$(function(){
    var JobList = function(container_elem, template_container_id) {
        this.elem = $(container_elem)
        this.searchConditions = {}
        this.searchUrl = window.bibos_job_search_url || './search/'
        this.statusSelectors = []
        BibOS.addTemplate('job-entry', template_container_id)
    }
    $.extend(JobList.prototype, {
        init: function() {
            var jobsearch = this
            $('#jobsearch-status-selectors input:checkbox').on("change", function() {
                jobsearch.search()
            })
            jobsearch.search()
        },

        appendEntries: function(dataList) {
            var container = this.elem
            $.each(dataList.results, function() {
                var info_button = ''
                if(this.has_info) {
                    info_button = '<div class="d-flex" id="jobsListButtonsDiv"><div ' +
                        'class="btn btn-secondary jobinfobutton p-0" ' +
                        `data-bs-title="Job-info
                        <div id='buttonDiv' class= 'd-flex' >
                            <div title='Kopier til udklipsholderen' class='spanDiv'>
                            <span id='clipboardButtonTop' title='Kopier til udklipsholderen' class='material-icons fs3'>content_copy</span>
                            </div>
                        ${makeRestartButtonIfJobFailed(this)}
                        <span id='closePopoverButton' title='Luk Job-info' class='material-icons fs-3'>close</span>
                        </div>" ` + // Hvad kan jeg gøre i stedet for at gange med 100, som er en lappeløsning, når jeg har brug for at få id'et med til genstart knappen, men allerede har brugt det til id'et for kopier knappen??
                        'data-bs-toggle="popover" ' +
                        'data-bs-content="Loading..." ' +
                        'data-bs-html=true ' +
                        'data-bs-placement=left ' +
                        'data-bs-trigger="click" ' +
                        'data-bs-animation="true" ' +
                        'data-pk="' + this.pk + '"' +
                        `><span class="material-icons fs-3">info
                            </span>
                        </div>
                        <div>
                        <span class='btn btn-secondary'>
                            <div class='clipboardCopyButtonsDiv'>
                                <span class='clipboardCopyButtons material-icons fs3' id='${this.pk}' title='Kopier log til udklipsholderen' class='material-icons fs3'>content_copy
                                </span>
                                <span id='messageForUserSpan${this.pk}'>
                                </span>
                            </div>
                        </span>
                    </div>
                    </div>`
                }

                var script_link = '<a href="' + this.script_url + '">' + this.script_name + '</a>'
                var pc_link = '<a href="' + this.pc_url + '">' + this.pc_name + '</a>'
                var user_link = this.user != ''? '<a href="' + this.user_url + '">' + this.user + '</a>' : 'Ingen bruger'
                var item = $(BibOS.expandTemplate(
                    'job-entry',
                    $.extend(this, {
                        'jobinfobutton': info_button,
                        'script_link' : script_link,
                        'pc_link' : pc_link,
                        'user_link': user_link
                    })
                ))
                item.find('input:checkbox').on("click", function() {
                    $(this).parents('tr').toggleClass('marked')
                })
                item.appendTo(container)
            })
            BibOS.setupJobInfoButtons(container)
        },

        replaceEntries: function(dataList) {
            this.elem.find('tr').remove()
            this.appendEntries(dataList)
        },

        selectFilter: function(field, elem, val) {
            var e = $(elem)
            e.parents('ul').find('button').removeClass('active')
            if(e.hasClass('active')) {
                val = ''
            } else {
                e.addClass('active')
            }
            $('#jobsearch-filterform input[name=' + field + ']').val(val)
            this.search()
        },

        selectBatch: function(elem, val) {
            this.selectFilter('batch', elem, val)
        },

        selectPC: function(elem, val) {
            this.selectFilter('pc', elem, val)
        },

        selectGroup: function(elem, val) {
            this.selectFilter('group', elem, val)
        },

        orderby: function(order) {
            var input = $('#jobsearch-filterform input[name=orderby]')
            input.val(BibOS.getOrderBy(input.val(), order))
            this.search()
        },
        setUpPaginationCount: function(data) {
            $("div#pagination-count").text(calcPaginationRange(data, 20))
        },
        setUpPaginationLinks: function(data) {
            var pagination = $("ul.pagination")
            pagination.empty()
            var jobsearch = this

            var previous_item = $('<li class="page-item disabled"><a class="page-link"><span class="material-icons">navigate_before</span> Forrige</a></li>')
            if (data.has_previous) {
                previous_item.removeClass("disabled")
                previous_item.find('a').on("click", function() {
                    var input = $('#jobsearch-filterform input[name=page]')
                    input.val(data.previous_page_number)
                    jobsearch.search()
                })
            }
            previous_item.appendTo(pagination)

            data.page_numbers.forEach(function(page) {
                if (data.page == page) {
                    item = $('<li class="page-item active"><a class="page-link"><strong><u>' + page + '</u></strong></a></li>')
                }
                else {
                    item = $('<li class="page-item"><a class="page-link">' + page + '</a></li>')
                }
                item.find('a').on("click", function() {
                    var input = $('#jobsearch-filterform input[name=page]')
                    input.val(page)
                    jobsearch.search()
                    addEventListenersToAllClipboardCopyButtons() // For at kopier knapperne virker når man trykker videre til de næste sider.
                })
                item.appendTo(pagination)
            })

            var next_item = $('<li class="page-item disabled"><a class="page-link">Næste <span class="material-icons">navigate_next</span></a></li>')
            if (data.has_next) {
                next_item.removeClass("disabled")
                next_item.find('a').on("click", function() {
                    var input = $('#jobsearch-filterform input[name=page]')
                    input.val(data.next_page_number)
                    jobsearch.search()
                })
            }
            next_item.appendTo(pagination)

        },
        search: function() {
            var js = this
            js.searchConditions = $('#jobsearch-filterform').serialize()
            $.ajax({
                type: "GET",
                url: js.searchUrl,
                data: js.searchConditions,
                success: function(data) {
                    js.replaceEntries(data)
                    js.setUpPaginationCount(data)
                    js.setUpPaginationLinks(data)
                },
                dataType: "json"
            })
        },

        reset: function() {
            $('#jobsearch-filterform')[0].reset()
            $('#jobsearch-filterform li.selected').removeClass('selected')
            $('#jobsearch-filterform input[name=batch]').val('')
            $('#jobsearch-filterform input[name=created]').val('')
            $('#jobsearch-filterform input[name=pc]').val('')
            $('#jobsearch-filterform input[name=group]').val('')
            $('#jobsearch-filterform input[name=page]').val('1')
            this.search()
        }
    })
    BibOS.JobList = new JobList('#job-list', '#jobitem-template')
    $(function() { BibOS.JobList.init() })
})
