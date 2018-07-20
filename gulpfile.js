var gulp = require('gulp'),
    config = require('./config.json'),
    sass = require('gulp-sass'),
    cleanCSS = require('gulp-clean-css'),
    include = require('gulp-include'),
    uglify = require('gulp-uglify'),
    autoprefixer = require('gulp-autoprefixer'),
    rename = require('gulp-rename'),
    jshint = require('gulp-jshint'),
    scsslint = require('gulp-scss-lint'),
    browserSync = require('browser-sync').create(),
    runSequence = require('run-sequence');

var config = {
  src: {
    scssPath: './src/scss',
    jsPath: './src/js'
  },
  dist: {
    cssPath: './static/css',
    jsPath: './static/js',
    fontPath: './static/webfonts'
  },
  htmlPath: './templates',
  pyPath: './manager',
  sync: config.sync,
  target: config.target,
  packagesPath: './node_modules',
};


//
// CSS
//

// Base linting function
function lintSCSS(src) {
  return gulp.src(src)
    .pipe(scsslint({
      'config': 'scss-lint-config.yml',
      'maxBuffer': 400 * 1024  // default: 300 * 1024
    }));
}

// Lint all project scss files
gulp.task('scss-lint-proj', function () {
  return lintSCSS(config.src.scssPath + '/**/*.scss');
});

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
      browsers: ['last 2 versions', 'not ie 10'],
      cascade: false
    }))
    .pipe(rename({
      extname: '.min.css'
    }))
    .pipe(gulp.dest(dest))
    .pipe(browserSync.stream());
}

// Compile project stylesheet
gulp.task('scss-build-proj', function () {
  return buildCSS(config.src.scssPath + '/style.scss');
});

// Process .scss files in /static/scss/
gulp.task('css', ['scss-lint-proj', 'scss-build-proj']);


//
// JavaScript
//

// Base JS linter function
function lintJS(src) {
  return gulp.src(src)
    .pipe(jshint())
    .pipe(jshint.reporter('jshint-stylish'))
    .pipe(jshint.reporter('fail'));
}

// Run jshint on all js files in src.jsPath (except already minified files.)
gulp.task('js-lint', function () {
  return lintJS([config.src.jsPath + '/*.js', '!' + config.src.jsPath + '/*.min.js']);
});

// Base JS concat + uglification function
function buildJS(src, dest) {
  dest = dest || config.dist.jsPath;

  return gulp.src(src)
    .pipe(include({
      includePaths: [config.packagesPath, config.src.jsPath]
    }))
    .on('error', console.log)
    .pipe(uglify())
    .pipe(rename({
      extname: '.min.js'
    }))
    .pipe(gulp.dest(dest))
    .pipe(browserSync.stream());
}

// Concat and uglify main js files
gulp.task('js-build-global', function () {
  return buildJS(config.src.jsPath + '/script.js');
});

// Concat and uglify email editor js files
gulp.task('js-build-email-designer-script', function () {
  return buildJS(config.src.jsPath + '/email-designer-script.js');
});

// Concat and uglify content lock script
gulp.task('js-build-lockcontent-script', function () {
  return buildJS(config.src.jsPath + '/lockcontent.js');
});

// All js-related tasks
gulp.task('js', function () {
  runSequence('js-lint', 'js-build-global', 'js-build-email-designer-script', 'js-build-lockcontent-script');
});


//
// Installation of components/dependencies
//

// Copy Font Awesome files
gulp.task('move-components-fontawesome', function() {
  gulp.src(config.packagesPath + '/@fortawesome/fontawesome-free/webfonts/**/*')
    .pipe(gulp.dest(config.dist.fontPath + '/fontawesome'));
});

// Athena Framework web font processing
gulp.task('move-components-athena-fonts', function () {
  return gulp.src([config.packagesPath + '/ucf-athena-framework/dist/fonts/**/*'])
    .pipe(gulp.dest(config.dist.fontPath + '/athena-framework'));
});

// Run all component-related tasks
gulp.task('components', [
  'move-components-fontawesome',
  'move-components-athena-fonts'
]);


// Rerun tasks when files change
gulp.task('watch', function() {
  if (config.sync) {
    browserSync.init({
        proxy: {
          target: config.target
        }
    });
  }

  gulp.watch(['./settings_local.py', './util.py', './urls.py']).on("change", browserSync.reload);
  gulp.watch(config.pyPath + '/**/*.py').on("change", browserSync.reload);
  gulp.watch(config.htmlPath + '/**/*.html').on("change", browserSync.reload);
  gulp.watch(config.src.scssPath + '/**/*.scss', ['css']);
  gulp.watch([config.src.jsPath + '/*.js', '!' + config.src.jsPath + '/*.min.js'], ['js']);
});

//
// Default task
//
gulp.task('default', function() {
  // Make sure 'components' completes before 'css' or 'js' are allowed to run
  runSequence('components', ['css', 'js']);
});
