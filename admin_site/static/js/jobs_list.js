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
                    info_button = '<button ' +
                        'class="btn jobinfobutton" ' +
                        'title="Job-info" ' +
                        'data-pk="' + this.pk + '"'+
                    '><i class="icon-info-sign"></i></button>'
                }
                var item = $(BibOS.expandTemplate(
                    'job-entry',
                    $.extend(this, {
                        'jobinfobutton': info_button
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
            $('.orderby').each(function() {
              if ($(this).hasClass('order-' + order)) {
                $(this).addClass('active').find('i').toggleClass('icon-chevron-down icon-chevron-up').addClass('icon-white')
              } else {
                $(this).removeClass('active').find('i').attr('class', 'icon-chevron-down')
              }
            })

            var input = $('#jobsearch-filterform input[name=orderby]')
            input.val(BibOS.getOrderBy(input.val(), order))
            this.search()
        },
        setUpPaginationCount: function(data) {
            $("div#pagination-count").text(calcPaginationRange(data))
        },
        setUpPaginationLinks: function(data) {
            var pagination = $("ul.pagination")
            pagination.empty()
            var jobsearch = this

            var previous_item = $('<li class="page-item disabled"><a class="page-link">Forrige</a></li>')
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
                    item = $('<li class="page-item active"><a class="page-link">' + page + '</a></li>')
                }
                else {
                    item = $('<li class="page-item"><a class="page-link">' + page + '</a></li>')
                }
                item.find('a').on("click", function() {
                    var input = $('#jobsearch-filterform input[name=page]')
                    input.val(page)
                    jobsearch.search()
                })
                item.appendTo(pagination)
            })

            var next_item = $('<li class="page-item disabled"><a class="page-link">Næste</a></li>')
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
            $('#jobsearch-filterform input[name=pc]').val('')
            $('#jobsearch-filterform input[name=group]').val('')
            $('#jobsearch-filterform input[name=page]').val('1')
            this.search()
        }
    })
    BibOS.JobList = new JobList('#job-list', '#jobitem-template')
    $(function() { BibOS.JobList.init() })
})