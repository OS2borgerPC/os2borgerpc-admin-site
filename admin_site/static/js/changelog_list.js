$(function(){
    class ChangelogList {
        constructor(container_elem, template_container_id) {
            this.elem = $(container_elem)
            this.searchConditions = {}
            this.searchUrl = window.changelog_search_url || './search/'
            this.tagSelectors = []
            BibOS.addTemplate('changelog-entry', template_container_id)
        }
    }
    $.extend(ChangelogList.prototype, {
        init: function() {
            let changelogsearch = this
            $('#changelogsearch-tag-selectors input:checkbox').on("change", function(){
                changelogsearch.search()
            })
            changelogsearch.search()
        },

        appendEntries: function(dataList) {
            let container = this.elem
            $.each(dataList.results, function() {
                let item = $(BibOS.expandTemplate(
                    'changelog-entry',
                    $.extend(this, {})))
                item.find('type:button').on("click", function() {
                    $(this).parents('div').toggleClass('marked')
                })
                for (const code of item[0].getElementsByTagName("code")) {
                    hljs.highlightElement(code)
                }
                item.appendTo(container)
            })
        },

        replaceEntries: function(dataList) {
            this.elem.find("div").remove()
            this.appendEntries(dataList)
        },

        setUpPaginationCount: function(data) {
            $("div#pagination-count").text(calcPaginationRange(data, 5))
        },

        setUpPaginationLinks: function(data) {
            let pagination = $("ul.pagination")
            pagination.empty()
            let changelogsearch = this

            let previous_item = $('<li class="page-item disabled"><a class="page-link"><span class="material-icons">navigate_before</span> Forrige</a></li>')
            if (data.has_previous) {
                previous_item.removeClass("disabled")
                previous_item.find('a').on("click", function() {
                    let input = $('#changelogsearch-filterform input[name=page]')
                    input.val(data.previous_page_number)
                    changelogsearch.search()
                })
            }
            previous_item.appendTo(pagination)

            data.page_numbers.forEach(function(page) {
                if (data.page == page) {
                    item = $('<li class="page-item active"><a class="page-link">' + page + '</a></li>')
                } else {
                    item = $('<li class="page-item"<a class="page-link">' + page + '</a></li>')
                }
                item.find('a').on("click", function() {
                    let input = $('#changelogsearch-filterform input[name=page]')
                    input.val(page)
                    changelogsearch.search()
                })
                item.appendTo(pagination)
            })

            let next_item = $('<li class="page-item disabled"><a class="page-link">Næste <span class="material-icons">navigate_next</span></a></li>')
            if (data.has_next) {
                next_item.removeClass("disabled")
                next_item.find('a').on("click", function() {
                    let input = $('#changelogsearch-filterform input[name=page]')
                    input.val(data.next_page_number)
                    changelogsearch.search()
                })
            }
            next_item.appendTo(pagination)
        },

        search: function(input = "") {
            let js = this
            js.searchConditions = $('#changelogsearch-filterform').serialize() + ((input != "") ? "&tag=" + input.name : "")
            $.ajax({
                type: "GET",
                url: js.searchUrl,
                data: js.searchConditions,
                success: (data) => {
                    js.replaceEntries(data)
                    js.setUpPaginationCount(data)
                    js.setUpPaginationLinks(data)
                },
                dataType: "json"
            })
        },

        reset: function() {
            $('#changelogsearch-filterform')[0].reset()
            $('#changelogsearch-filterform li.selected').removeClass('selected')
            $('#changelogsearch-filterform input[name=page]').val('1')
            this.search()
        }
    })
    BibOS.ChangelogList = new ChangelogList('#changelog-list', '#changelogitem-template')
    $(function() { BibOS.ChangelogList.init() })
})
