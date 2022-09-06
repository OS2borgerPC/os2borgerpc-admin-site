(function(BibOS, $) {
    BibOS.addTemplate('script-input', '#script-input-template')

    ScriptEdit = function() {
        this.reload = false
        this.iframeCount = 0
    }
    $.extend(ScriptEdit.prototype, {
        init: function() {
            this.modal = $('#runscriptmodal')
            this.modalHeader = $('#runscriptmodalheader')
            this.modalFooter = $('#runscriptmodalfooter')
            this.modalIframe = $('#runscriptmodaliframe')
            var b = this
            this.modal.on('show', function() {
                if(b.reload) {
                    b.modalIframe.attr('src', b.defaultIframeSrc)
                } else {
                    b.defaultIframeSrc = b.modalIframe.attr('src')
                    b.reload = true
                }
            })

            // Dispatch event for updateDialog() to react upon
            setTimeout(function() {
                const iframe = document.getElementById('runscriptmodaliframe')
                if (iframe) {
                    iframe.contentWindow.postMessage('please run updateDialog', '*')
                }
            }, 1000)
        },
        setModalLoading: function() {
            var modal = $('#runscriptmodal')
            if(this.modalDefaultHTML) {
                modal.html(this.modalDefaultHTML)
            } else {
                this.modalDefaultHTML = modal.html()
            }
        },
        setModalContent: function(html) {
            $('#runscriptmodal').html(html)
        },
        addInput: function (id, data_in) {
            var container = $(id)
            if (!data_in)
                data_in = {}
            var count = container.find('tr.script-input').length
            var data = $.extend(
                {
                    pk: '',
                    position: count || 0,
                    name: '',
                    value_type: 'STRING',
                    mandatory: true,
                    name_error: '',
                    type_error: ''
                },
                data_in
            )
            var elem = $(BibOS.expandTemplate(
                'script-input',
                data
            ))
            elem.find('input.mandatory-input')[0].checked = elem.find('input.mandatory-input')[0].value != "false"
            elem.find('select').val(data['value_type'])
            if (elem.find('select')[0].value == "BOOLEAN") {
                elem.find('input.mandatory-input')[0].disabled = true
            }
            elem.find('select')[0].addEventListener("change", type_check)
            elem.insertBefore(container.find('tr.script-input-add').first())
            this.updateInputNames(id)
        },
        removeInput: function(elem) {
            var container = $(elem).parents('fieldset').first()
            $(elem).remove()
            this.updateInputNames(container)
        },
        updateInputNames: function(id) {
            var container = $(id)
            inputs = container.find('tr.script-input')
            inputs.each(function(i, e) {
                var elem = $(e)
                elem.find('input.pk-input').attr('name', 'script-input-' + i + '-pk')
                elem.find('input.name-input').attr('name', 'script-input-' + i + '-name')
                elem.find('select.type-input').attr('name', 'script-input-' + i + '-type')
                elem.find('input.mandatory-input').attr('name', 'script-input-' + i + '-mandatory')
            })
            container.find('input.script-number-of-inputs').val(inputs.length)
        }
    })

    BibOS.ScriptEdit = new ScriptEdit()
    $(function() { BibOS.ScriptEdit.init() })
})(BibOS, $)

/* Syntax highlighting */
const code = document.getElementById("script-code")
hljs.highlightElement(code)

function type_check(event) {
    /* The index of the relevant input line is extracted from the name of the triggering event,
     which has the form "script-input-i-type," where i is the index.
     The desired index for this function is 1 greater than the index of the input line because
     the list of all checkboxes also contains the checkbox template at index 0. */
    index = event.target.name.slice(13, -5), ++index
    checkboxes = document.getElementsByClassName("mandatory-input")
    if (event.target.value == "BOOLEAN") {
        checkboxes[index].checked = false
        checkboxes[index].disabled = true
        checkboxes[index].value = "false"
    } else {
        checkboxes[index].disabled = false
        checkboxes[index].checked = true
        checkboxes[index].value = "true"
    }
}