const fs           = require('fs');
const browserSync  = require('browser-sync').create();
const gulp         = require('gulp');
const autoprefixer = require('gulp-autoprefixer');
const cleanCSS     = require('gulp-clean-css');
const include      = require('gulp-include');
const eslint       = require('gulp-eslint');
const isFixed      = require('gulp-eslint-if-fixed');
const babel        = require('gulp-babel');
const rename       = require('gulp-rename');
const sass         = require('gulp-sass')(require('sass'));
const sassLint     = require('gulp-sass-lint');
const uglify       = require('gulp-uglify');
const merge        = require('merge');


let config = {
  src: {
    scssPath: './src/scss',
    jsPath: './src/js'
  },
  dist: {
    cssPath: './static/css',
    jsPath: './static/js',
    fontPath: './static/webfonts'
  },
  packagesPath: './node_modules',
  htmlPath: './templates',
  pyPath: './manager',
  sync: false,
  syncTarget: 'http://127.0.0.1:8000'
};

/* eslint-disable no-sync */
if (fs.existsSync('./gulp-config.json')) {
  const overrides = JSON.parse(fs.readFileSync('./gulp-config.json'));
  config = merge(config, overrides);
}
/* eslint-enable no-sync */


//
// Helper functions
//

// Base SCSS linting function
function lintSCSS(src) {
  return gulp.src(src)
    .pipe(sassLint())
    .pipe(sassLint.format())
    .pipe(sassLint.failOnError());
}

// Base SCSS compile function
function buildCSS(src, dest) {
  dest = dest || config.dist.cssPath;

  return gulp.src(src)
    .pipe(sass({
      includePaths: [config.src.scssPath, config.packagesPath]
    })
      .on('error', sass.logError))
    .pipe(cleanCSS())
    .pipe(autoprefixer({
      // Supported browsers added in package.json ("browserslist")
      cascade: false
    }))
    .pipe(rename({
      extname: '.min.css'
    }))
    .pipe(gulp.dest(dest));
}

// Base JS linting function (with eslint). Fixes problems in-place.
function lintJS(src, dest) {
  dest = dest || config.src.jsPath;

  return gulp.src(src)
    .pipe(eslint({
      fix: true
    }))
    .pipe(eslint.format())
    .pipe(isFixed(dest));
}

// Base JS compile function
function buildJS(src, dest) {
  dest = dest || config.dist.jsPath;

  return gulp.src(src)
    .pipe(include({
      includePaths: [config.packagesPath, config.src.jsPath]
    }))
    .on('error', console.log) // eslint-disable-line no-console
    .pipe(babel())
    .pipe(uglify())
    .pipe(rename({
      extname: '.min.js'
    }))
    .pipe(gulp.dest(dest));
}

// BrowserSync reload function
function serverReload(done) {
  if (config.sync) {
    browserSync.reload();
  }
  done();
}

// BrowserSync serve function
function serverServe(done) {
  if (config.sync) {
    browserSync.init({
      proxy: {
        target: config.syncTarget
      }
    });
  }
  done();
}


//
// Installation of components/dependencies
//

// Copy Font Awesome files
gulp.task('move-components-fontawesome-fonts', (done) => {
  gulp.src(`${config.packagesPath}/@fortawesome/fontawesome-free/webfonts/**/*`)
    .pipe(gulp.dest(`${config.dist.fontPath}/fontawesome`));
  done();
});

// Athena Framework web font processing
gulp.task('move-components-athena-fonts', (done) => {
  gulp.src(`${config.packagesPath}/ucf-athena-framework/dist/fonts/**/*`)
    .pipe(gulp.dest(`${config.dist.fontPath}/athena-framework`));
  done();
});

// Run all component-related tasks
gulp.task('components', gulp.parallel(
  'move-components-fontawesome-fonts',
  'move-components-athena-fonts'
));


//
// CSS
//

// Lint all project scss files
gulp.task('scss-lint', () => {
  return lintSCSS(`${config.src.scssPath}/*.scss`);
});

// Compile project stylesheet
gulp.task('scss-build-proj', () => {
  return buildCSS(`${config.src.scssPath}/style.scss`);
});

// Process .scss files in /static/scss/
gulp.task('css', gulp.series('scss-lint', 'scss-build-proj'));


//
// JavaScript
//

// Run eslint on all js files in src.jsPath (except already minified files.)
gulp.task('es-lint', () => {
  return lintJS(
    [
      `${config.src.jsPath}/*.js`,
      `!${config.src.jsPath}/*.min.js`
    ]
  );
});

// Concat and uglify main js files
gulp.task('js-build-global', () => {
  return buildJS(`${config.src.jsPath}/script.js`);
});

// Concat and uglify content lock script
gulp.task('js-build-lockcontent-script', () => {
  return buildJS(`${config.src.jsPath}/lockcontent.js`);
});

// All js-related tasks
gulp.task('js', gulp.series(
  'es-lint',
  'js-build-global',
  'js-build-lockcontent-script'
));


//
// Rerun tasks when files change
//
gulp.task('watch', (done) => {
  serverServe(done);

  gulp.watch(['./settings_local.py', './util.py', './urls.py'], gulp.series(serverReload));
  gulp.watch(`${config.pyPath}/**/*.py`, gulp.series(serverReload));
  gulp.watch(`${config.htmlPath}/**/*.html`, gulp.series(serverReload));
  gulp.watch(`${config.src.scssPath}/**/*.scss`, gulp.series('css', serverReload));
  gulp.watch([`${config.src.jsPath}/**/*.js`, `!${config.src.jsPath}/*.min.js`], gulp.series('js', serverReload));
});


//
// Default task
//
gulp.task('default', gulp.series('components', gulp.parallel('css', 'js')));
