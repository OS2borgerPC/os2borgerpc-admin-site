import autoprefixer from 'autoprefixer'
import postcss from 'postcss'
import fs from 'fs'

fs.readFile('dist/css/custom.css', (err, css) => {
    postcss([autoprefixer])
    .process(css, { from: 'dist/css/custom.css', to: 'dist/css/bootstrap.css' })
    .then(result => {
        fs.writeFile('dist/css/bootstrap.css', result.css, () => true)
        if ( result.map ) {
            fs.writeFile('dist/css/bootstrap.css.map', result.map.toString(), () => true)
        }
    })
})