// Set up global BibOS instance used for accessing utility methods
var BibOS
(function($) {
  function BibOS(args) {
    this.templates = {}
    this.documentReady = false
    this.loadedItems = {}
    this.scriptsToLoad = []
    this.cssToLoad = []
    this.shownJobInfo = -1
  }

  var documentation_match = /^(https?:\/\/[^\/]+)?\/documentation\//
  var back_match = /[\?\&]back=([^\&]+)/

  $.extend(BibOS.prototype, {
    init: function() {
    },

    onDOMReady: function() {
      var t = this
      t.documentReady = true

      // Mark what we have already loaded
      $('script').each(function() {
        t.loadedItems[$(this).attr('src') || ''] = true
      })
      $.each(this.scriptsToLoad, function() {
        t.loadScript(this)
      })
      $('link').each(function() {
        t.loadedItems[$(this).attr('href') || ''] = true
      })
      $.each(this.cssToLoad, function() {
        t.loadStylesheet(this)
      })

      $('#editconfig_value').attr('maxlength', 4096)

      var m = document.cookie.match(/\bpage-notification\s*=\s*([^;]+)/)
      if(m) {
        try {
          var descriptor = JSON.parse(decodeURIComponent(m[1]))
          notification = $('.page-notification').first()
          if (descriptor["type"] == "error") {
            notification.addClass("alert-danger")
          } else {
            notification.addClass("alert-success")
          }
          notification.toggleClass(["d-block", "d-none"])
          notification.html(descriptor["message"]).fadeIn()
        } catch (e) {
          /* If there was an exception here, then the cookie was malformed --
             print the exception to the console and continue, clearing the
             broken cookie */
          console.error(e)
        }
        document.cookie = 'page-notification=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/'
      }

      if(location.href.match(documentation_match))
      {
        this.setupDocumentationBackLinks()
      }

      // TODO: With this we can link directly to a specific tab
      // The functionality can be used to make tab forms redirect to whatever the current tab is, after pressing "Save" on
      // the form.
      // Example: This URL should go directly to site configs. It also stays focused, though, which
      // should be removed if we decide to go with this solution
      // http://localhost:9999/site/magenta/settings/#configs-tab
      // In other words you trigger it based off the ID of the button activating it, rather than the ID of the tab
      // itself.
      if (window.location.hash) {
        var someTabTriggerEl = document.querySelector(window.location.hash)
        var tab = new bootstrap.Tab(someTabTriggerEl)
        tab.show()
        // Now remove the tab's highlighting
        tab._element.blur()
      }

    },
    setupDocumentationBackLinks: function() {
      var ref = document.referrer || ''
      var back = ''

      var m = ref.match(back_match) || location.href.match(back_match)
      if(m) {
        back = unescape(m[1])
      } else if(!ref.match(documentation_match)) {
        back = ref
      }

      if(! back)
        return

      back = escape(back)
      $('a').each(function() {
        var href = $(this).attr('href') || ''
        if(href == '#' || href.match(/^javascript:/))
          return true
        if(href.match(documentation_match)) {
          var url_parts = href.split(/[\?#]/)
          var qstring_parts = (url_parts[1] || '').split('&')
          var args = []
          $.each(qstring_parts, function() {
            if(this != '' && !this.match(/back=/))
              args.push(this)
          })
          args.push('back=' + back)
          var new_href = [
            url_parts[0],
            '?', args.join('&'),
          ].join('')
          if(url_parts.length > 2) {
            url_parts.splice(0, 2)
            new_href += '#' + url_parts.join("#")
          }
          $(this).attr('href', new_href)
        }
        return true
      })
    },
    loadResource: function(type, src) {
      if(this.documentReady) {
        var item
        if(this.loadedItems[src])
          return
        if(type == 'css' || type == 'stylesheet') {
          var css = $('<link>', {
            'href': src,
            'type': 'text/css',
            'rel': 'stylesheet'
          })
          css.appendTo($('head'))
        } else if(type == 'script' || type == 'javascript') {
          var script = $('<script>', {'src': src, 'type':'text/javascript'})
          script.appendTo($('body'))
        } else {
          alert("Don't know how to load item of type " + type)
          return
        }
        this.loadedItems[src] = true
      } else {
        if (type == 'css' || type == 'stylesheet') {
          this.cssToLoad.push(src)
        } else if(type == 'script') {
          this.scriptsToLoad.push(src)
        } else {
          alert("Don't know how to load item of type " + type + ' once')
        }
      }
    },

    loadScript: function(src) {
      this.loadResource('script', src)
    },

    loadStylesheet: function(src) {
      this.loadResource('css', src)
    },

    translate: function() {
      // TODO: implement actual translation, this is just poor man's sprintf
      var args = arguments, arg_idx = 1, key = arguments[0] || ''
      if (arguments.length > 1) {
        key = key.replace(/\%s/g, function(m) {
          var v = args[arg_idx++]
          return v == undefined ? '' : v
        })
      }
      return key
    },

    // Load a template from innerHTML of element specified by id
    addTemplate: function(name, id) {
      this.templates[name] = $(id).html()
    },

    // Expand a template with the given data
    expandTemplate: function(templateName, data) {
      var html = this.templates[templateName] || ''
      var expander = function(fullmatch, key) {
          k = key.toLowerCase()
          return k in data ? data[k] : fullmatch
      }
      html = html.replace(/<!--#([^#]+)#-->/g, expander)
      return html.replace(/#([^#]+)#/g, expander)
    },

    getCookie: function (name) {
      var cookieValue = null
      if (document.cookie && document.cookie != '') {
          var cookies = document.cookie.split(';')
          for (var i = 0; i < cookies.length; i++) {
              var cookie = cookies[i].trim()
              // Does this cookie string begin with the name we want?
              if (cookie.substring(0, name.length + 1) == (name + '=')) {
                  cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
                  break
              }
          }
      }
      return cookieValue
    },
    csrfSafeMethod: function (method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method))
    },
    sameOrigin: function (url) {
        // test that a given url is a same-origin URL
        // url could be relative or scheme relative or absolute
        var host = document.location.host // host + port
        var protocol = document.location.protocol
        var sr_origin = '//' + host
        var origin = protocol + sr_origin
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url))
    },
    getOrderBy: function(old_order, new_order) {
      var desc = false,
          old_desc = false
      if (old_order.match(/^\-/)) {
          old_order = old_order.replace(/^\-/, '')
          old_desc = true
      }
      if (new_order == old_order)
          desc = !old_desc
      return (desc ? '-' : '') + new_order
    },
    setOrderByClasses: function(elem, list, orderkey) {
      $(list).removeClass('orderby').removeClass('orderby-desc')
      $(elem).addClass(orderkey.match(/^-/) ? 'orderby-desc' : 'orderby')
    },
    insertToOrderedList: function(topElem, selector, matcher, elem, defaultInsertCallback) {
      var inserted = false,
        lastInsert = defaultInsertCallback || function() {
          elem.detach().appendTo($(topElem))
        }

      $(topElem).children(selector).each(function() {
        var currentElem = $(this)
        if(matcher(currentElem)) {
          elem.detach().insertBefore(currentElem)
          inserted = true
        }
        return !inserted
      })

      if(!inserted)
        lastInsert(elem)
    },
    setupJobInfoButtons: function(rootElem) {
      // initialize all popovers.
      var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
      var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
      })

      var t = this

      // JOBINFOBUTTON
      $(rootElem).find('.jobinfobutton').on('show.bs.popover', function(e) {
        // hide all popovers before a new popover is shown.
        popoverTriggerList.map(function (popoverTriggerEl) {
          $(popoverTriggerEl).popover('hide')
        })
      })

      $(rootElem).find('.jobinfobutton').on('shown.bs.popover', function(e) {
        t.showJobInfo(this)
      })
    },
    setupSecurityEventLogInfoButtons: function(rootElem) {
      // initialize all popovers.
      var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
      var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
      })

      var t = this

      $(rootElem).find('.loginfobutton').on('show.bs.popover', function(e) {
        // hide all popovers before a new popover is shown.
        popoverTriggerList.map(function (popoverTriggerEl) {
          $(popoverTriggerEl).popover('hide')
        })
      })
    },
    showJobInfo: function(triggerElem) {
      var t = this
      var popover = bootstrap.Popover.getInstance(triggerElem)
      triggerElem = $(triggerElem)
      var id = triggerElem.attr('data-pk')
      this.shownJobInfo = id
      var url = location.href.match(/^(https?:\/\/[^\/]+\/site\/[^\/]+\/)/)
      if (url) {
        url = url[1] + 'jobs/' + id + '/info/'
      } else {
        return false
      }
      $.ajax({
        'type': 'GET',
        'url': url,
        'success': function(data) {
          // set content from backend data and redraw popover.
          triggerElem.attr("data-bs-content", data)
          popover.setContent()

          const parser = new DOMParser();
          const dataHTML = parser.parseFromString(data, 'text/html');

          const jobLog = dataHTML.getElementById("job-log").innerText

          addEventListenerForClipBoardButton(jobLog)
        },
        'error': function() {
        }
      })
      return false
    },
  })
  window.BibOS = window.BibOS || new BibOS()
  var b = window.BibOS
  b.init()
  $(function() { b.onDOMReady() })

  //(Setup support for CSRFToken in ajax calls
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!b.csrfSafeMethod(settings.type) && b.sameOrigin(settings.url)) {
        // Send the token to same-origin, relative URLs only.
        // Send the token only if the method warrants CSRF protection
        // Using the CSRFToken value acquired earlier
        xhr.setRequestHeader("X-CSRFToken", b.getCookie('csrftoken'))
      }
    }
  })

})($)

/* Utility function to calculate some pagination numbers */
function calcPaginationRange(pag_data, obj_per_page) {
  const first = ((pag_data.page - 1) * obj_per_page ) + 1
  const last = ((pag_data.page - 1) * obj_per_page ) + pag_data.results.length
  const range = first + "-" + last + " af " + pag_data.count
  return range
}

/* Feature to warn users with old IE browsers */
function oldBrowserWarning() {
  var old_ie_match = /MSIE/g
  var ie11_win8_match = /Windows NT.+Trident/g
  var ie11_win10_match = /Windows NT 10.+Trident/g
  var ua = navigator.userAgent
  var warn_el = document.querySelector('ie11-browser-warning')

  if (ua.match(ie11_win10_match)) {
      warn_el.innerHTML = ''
          + '<p>' + warn_el.dataset.warningText +'</p>'
          + '<p><a href="microsoft-edge:' + window.location.href + '">' + warn_el.dataset.linkText +'</a></p>'
  } else if (ua.match(ie11_win8_match) || ua.match(old_ie_match)) {
      warn_el.innerHTML = '<p>' + warn_el.dataset.warningText + '</p>'
  } else {
      warn_el.remove()
  }
}

window.addEventListener('load', function() {
  oldBrowserWarning()
})

// Function to get the value of a named cookie
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

/* Currently only used by the job log copy button */
function addEventListenerForClipBoardButton(log) {
  let btn = document.getElementById("clipboard-button")

  btn.addEventListener('click', () => {

    navigator.clipboard.writeText(log)

    btn.getElementsByClassName("copy-btn-text-orig")[0].classList.add('d-none')
    btn.lastElementChild.classList.remove('d-none')
  })
}

/* General purpose copy button */
/* It expects to receive a parent element containing elements with the classes:
 * copy-btn: The button to attach the event listener to, which copies
 * copy-text: The element containing the text to copy
 * after-copy-text: The element containing the text to be shown after copying
*/
function copy_button(el) {
  const btn = el.getElementsByClassName('copy-btn')[0]

  btn.addEventListener('click', () => {

    const text_to_copy = el.getElementsByClassName('copy-text')[0].innerText
    const el_to_show_after_copy = el.getElementsByClassName('after-copy-text')[0]

    // Remove the ugly focus brorder around the btn after clicking it
    btn.blur()

    navigator.clipboard.writeText(text_to_copy)

    el_to_show_after_copy.classList.remove('d-none')
  })
}

function copy_api_key(event) {
  const btn = event.currentTarget
  btn.blur() // Remove the focus around the button after copying
  navigator.clipboard.writeText(btn.parentElement.firstElementChild.innerText)
  btn.parentElement.lastElementChild.classList.remove('d-none')
}
