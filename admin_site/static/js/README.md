# Overview

Each JavaScript file in this project, and a brief description of its role:

| Name                    | Description                                                                                                                                                          |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| changelog_list.js       | Handles Changelog/News, specifically syntax highlighting of code and showing/hiding various levels of comments                                                       |
| configlist.js           |                                                                                                                                                                      |
| custom.js               | General JavaScript, either things used globally or small blobs of JavaScript for specific pages                                                                      |
| jobs_list.js            |                                                                                                                                                                      |
| policy_list.js          |                                                                                                                                                                      |
| script_edit.js          |                                                                                                                                                                      |
| script_search.js        |                                                                                                                                                                      |
| security_events_list.js |                                                                                                                                                                      |
| wake_change_event.js    | Handle ability to return to the last visited wake plan, setting some required fields as required and making it faster to setup a wake change event through auto fill |
| wake_plan.js            | Handle ability to return to the last visited wake planHandle switches,                                                                                               |

## Configlist

It's used to generate the config list for both Computers, Groups and the Site.

How it works:

File loading sequence:
Main page loads: configlist.js, templates.html and list.html
list.html loads item.html for each item in the list on the overview page
templates.html **also** loads item.html, but for a specific item that's being edited?

There are five relevant files:

| File           | Description                                                                                                                         |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| A main page    | Either site_settings.html, site_groups.html or pcs/form.html. It loads list.html and templates.html and passes context data to them |
| templates.html | Contains the edit modal, and therefore the form.                                                                                    |
| list.html      | Loads item.html and passes context to it                                                                                            |
| item.html      | Handles how each config is shown on the main list. When templates.html loads it, it's within a form                                 |
| configlist.js  |                                                                                                                                     |
