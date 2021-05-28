# Admin Site UI elements

TODO

* errors
* icons
* giant popover
* old browser warning?

* Lav sag: Redigering af konfiguration er broken. 
  Se f.eks. http://localhost:9999/site/magenta/computers/computer3/#configs

## Pick list
Styles in nodejs/src/_picklist.scss

**Example**
```
<div class="pick-list">
    <ul class="pick-list-selected list-group">
        <li class="list-group-item list-group-item-action">
            <button 
                class="btn btn-link d-flex align-items-center pick-list-dropdown-btn" 
                type="button" 
                id="pick-list-dropdown" 
                data-bs-toggle="dropdown" 
                aria-expanded="false">
                <span class="material-icons">add</span>
                Tilføj xxxx
            </button>
            <ul class="pick-list-available dropdown-menu" aria-labelledby="pick-list-dropdown">
                <li class="dropdown-item">
                    Item to pick
                </li>
                ...
            </ul>
        </li>
        <li class="list-group-item pick-list-item">
            Picked item
        </li>
        ...
    </ul>
</div>
```

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

## Layout

### Gray box
Styles in nodejs/src/_layout.scss
Turns a containing element into a nice box with gray background.

**Example**
```
<form class="gray-box"
    ...
</form>
```


## Content

### Code view
Styles in nodejs/src/_code.scss
Styling for HighlightJS (lhjs) code blocks.

**Example**
```
<code class="hljs>
    ...
</code>
```

### Bordered gray box
Styles in nodejs/src/_layout.scss
For configuration tables, etc

**Example**
```
<div class="gray-box-border">
    ...
</div>
```
