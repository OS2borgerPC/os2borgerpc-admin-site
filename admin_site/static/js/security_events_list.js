$(function(){
    var SecurityEventList = function(container_elem, template_container_id) {
        this.elem = $(container_elem)
        this.searchUrl = window.bibos_security_event_search_url
        this.statusSelectors = []
        BibOS.addTemplate('securityevent-entry', template_container_id)
    }
    $.extend(SecurityEventList.prototype, {
        init: function() {
            var securityeventsearch = this
            $('#securityeventsearch-status-selectors input:checkbox').on("change", function() {
                securityeventsearch.search()
            })
            $('#securityeventsearch-level-selectors input:checkbox').on("change", function() {
                securityeventsearch.search()
            })
            securityeventsearch.search()
        },

        appendEntries: function(dataList) {
            var container = this.elem
            $.each(dataList.results, function() {
                var item = $(BibOS.expandTemplate(
                    'securityevent-entry',
                    $.extend(this, {})
                ))
                item.attr('onclick', "location.href = '/site/" + this.site_uid + "/security/" + this.pk + "/'")
                item.appendTo(container)
            })
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
            $('.orderby').each(function() {
              if ($(this).hasClass('order-' + order)) {
                $(this).addClass('active').find('i').toggleClass('icon-chevron-down icon-chevron-up').addClass('icon-white')
              } else {
                $(this).removeClass('active').find('i').attr('class', 'icon-chevron-down')
              }
            })

            var input = $('#securityeventsearch-filterform input[name=orderby]')
            input.val(BibOS.getOrderBy(input.val(), order))
            this.search()
        },
        setUpPaginationCount: function(data) {
            $("div#pagination-count").text(data.results.length + " - " + data.count)
        },
        setUpPaginationLinks: function(data) {
            var pagination = $("ul.pagination")
            pagination.empty()

            var eventsearch = this
            for (i = 1; i < data.num_pages + 1; i++) {
                let j = i
                var item = $('<li class="page-item"><a class="page-link">' + j + '</a></li>')
                item.find('a').on("click", function() {
                    var input = $('#securityeventsearch-filterform input[name=page]')
                    input.val(j)
                    eventsearch.search()
                })
                item.appendTo(pagination)
            }
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
