# Customizing styles for OS2BorgerPC admin_site

OS2BorgerPC admin_site styles are based on a customized Bootstrap v5 build.

This is a guideline for further customizing the site.

## Step 0: Install dependencies

First off, you'll need to install the NodeJS dependencies to build Bootstrap.
**You need only do this once.**
From [nodejs/](./) directory, install dependencies. 
(Assuming you have [NodeJS](https://nodejs.org/en/) and [npm](https://www.npmjs.com/) installed.)
```
$ npm install
```
This also installs the Bootstrap base styles, which you'll customize.

## Step 1: Edit SCSS

[nodejs/src/](./src) contains the customized SASS styles. 
Add or edit styles in the files contained here.
If you add a new `.scss` file, be sure to import it into [custom.scss](./src/custom.scss)

Be sure to look into [_variables.scss](./src/_variables.scss). The SASS variables in this file are used to tweak Bootstrap variables in a standardized way. 
We highly encourage you to start any attempt at customization by just tweaking the variables. [Read more about default variables in the Bootstrap docs.](https://getbootstrap.com/docs/5.0/customize/sass/#variable-defaults)

## Step 2: Build CSS

From [nodejs/](./) directory, run the npm `build` script.
```
$ npm run build
```
This compiles the base Bootstrap styles and your custom styles into a `bootstrap.css` file that is stored in the [static/css](../admin_site/static/css/bootstrap.css).

You should be able to run the admin site application in a browser and see your changes.