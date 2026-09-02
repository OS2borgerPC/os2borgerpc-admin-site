import markdown
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def markdown_format(text):
    # Escape any raw HTML in the input BEFORE running markdown, so text stored
    # in e.g. a script description cannot inject live HTML/JS (stored XSS).
    # Markdown formatting (bold, lists, links, ...) still works, because that
    # uses markdown syntax rather than raw HTML. python-markdown 3.x has no
    # safe_mode, so sanitising the input is the dependency-free way to do this.
    return mark_safe(markdown.markdown(escape(text or "")))
