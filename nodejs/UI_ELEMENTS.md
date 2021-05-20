# Admin Site UI elements

TODO

* lists
* form buttons
* form elements
* icons
    
## Itemlist (sublevelnav)
Styles in nodejs/src/_itemlist.scss

**Example**
```
<ul class="item-list">
    <li class="disabled>
        Disabled element
    </li>
    <li class="active>
        <a class="item-list-link" href="#">
            Go somewhere
        </a>
    </li>
    <li>
        <a class="item-list-link" href="#">
            Go somewhere else
        </a>
    </li>
</ul>
```

### Item list utilities
Styles in nodejs/src/_navigation.scss

**Example**
```
<div class="sublevelnav">
    <div class="listutils">
        <button>Does something</button>
    </div>
    ...
</div>
```

### Deletable elements in itemlist
Styles in nodejs/src/_itemlist.scss

**Example**
```
<ul class="item-list">
    <li>
        <a class="item-list-link" href="#">
            Thing that can be deleted
        </a>
        <a class="item-list-deletable material-icons" href="#" title="Delete the ting">
            clear
        </a>
    </li>
</ul>
```

### Collapsible elements in itemlist
Styles in nodejs/src/_collapsible.scss
 
**Example**
```
<div class="list-collapsible">
    <a data-bs-toggle="collapse" href="#collapseId" role="button" aria-expanded="false" aria-controls="collapseId">
        <span class="material-icons">folder</span>
        <span class="collapse-label">
            ... collapse button label ...
        </span>
        <span class="material-icons collapse-arrow">arrow_drop_down</span>
    </a>
    <ul class="item-list collapse collapse-content" id="collapseId">
        ...
    </ul>
</div>
```


- main nav / _navigation.scss
- main header / _layout.scss

-- itemlist tabs
-- itemlist collapsible
- filters (subnav)
- content header / _layout.scss
- table
- form
- tabs
- button, primary (save)
- button, secondary (cancel)
- button, highlighted (kør script)
- modal dialog
- code view (pre)
- contentlist (dark table)
- giant popover
- pagination
- collapsible list group / _collapsible.scss
