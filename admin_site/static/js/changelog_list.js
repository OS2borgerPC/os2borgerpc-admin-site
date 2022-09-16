// Run highlight js on all code tags
$(window).on("load", function() {
    for (const code of document.getElementsByTagName("code")) {
        document.gete
        hljs.highlightElement(code)
    }
})


function toggleCommentForm(pk) {
    replyForm = document.getElementById("reply-form-" + pk)
    toggleButton = document.getElementById("reply-toggle-button-" + pk)

    replyForm.style.display = replyForm.style.display == "none" ? "block" : "none" 
    toggleButton.style.display = replyForm.style.display == "none" ? "block" : "none"
}

function toggleCommentChildren(pk, children) {
    commentChildren = document.getElementById("comment-children-" + pk)
    toggleButton = document.getElementById("comment-children-toggle-button-" + pk)

    commentChildren.style.display = commentChildren.style.display == "none" ? "block" : "none"
    toggleButton.innerText = commentChildren.style.display == "block" ? "Gem svar" : "Vis " + children + " svar"
}
