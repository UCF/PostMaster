var gulp = require('gulp'),
    config = require('./config.json'),
    sass = require('gulp-sass'),
    minifyCss = require('gulp-minify-css'),
    bless = require('gulp-bless'),
    concat = require('gulp-concat'),
    uglify = require('gulp-uglify'),
    prefix = require('gulp-autoprefixer'),
    rename = require('gulp-rename'),
    jshint = require('gulp-jshint'),
    scsslint = require('gulp-scss-lint'),
    browserSync = require('browser-sync').create(),
    reload = browserSync.reload;

var config = {
  sassPath: './static/scss',
  cssPath: './static/css',
  jsPath: './static/js',
  fontPath: './static/fonts',
  htmlPath: './',
  sync: config.sync,
  target: config.target,
};


// Process .scss files in /static/scss/
gulp.task('css', function() {
  return gulp.src(config.sassPath + '/*.scss')
    .pipe(scsslint({
      'config': 'scss-lint-config.yml',
    }))
    .pipe(sass().on('error', sass.logError))
    .pipe(prefix({
        browsers: ["last 3 versions"],
        cascade: false
    }))
    .pipe(minifyCss())
    .pipe(rename('style.min.css'))
    .pipe(gulp.dest(config.cssPath))
    .pipe(browserSync.stream());
});


// Lint, concat and uglify js files.
gulp.task('js', function() {

  // Run jshint on all js files in jsPath (except already minified files.)
  return gulp.src([config.jsPath + '/*.js', '!' + config.jsPath + '/*.min.js'])
    .pipe(jshint())
    .pipe(jshint.reporter('jshint-stylish'))
    .pipe(jshint.reporter('fail'))
    .on('end', function() {

      // Combine and uglify js files to create script.min.js.
      var minified = [
        config.jsPath + '/instance.js',
        config.jsPath + '/recipients.js',
        config.jsPath + '/recipientgroup-update.js',
        config.jsPath + '/global.js',
      ];

      gulp.src(minified)
        .pipe(concat('script.min.js'))
        .pipe(uglify())
        .pipe(gulp.dest(config.jsPath))
        .pipe(browserSync.stream());

      // Combine and uglify email designer js files to create email-designer-script.min.js.
      var designerMinified = [
        config.jsPath + '/froala.min.js',
        config.jsPath + '/froala-font_size.min.js',
        config.jsPath + '/froala-media_manager.min.js',
        config.jsPath + '/email-designer-editor.js',
      ];

      gulp.src(designerMinified)
        .pipe(concat('email-designer-script.min.js'))
        .pipe(uglify())
        .pipe(gulp.dest(config.jsPath))
        .pipe(browserSync.stream());

    });
});


// Rerun tasks when files change
gulp.task('watch', function() {
  if (config.sync) {
    browserSync.init({
        proxy: {
          target: config.target
        }
    });
  }

  gulp.watch(config.htmlPath + '/*.py');
  gulp.watch(config.htmlPath + '/*.html');
  gulp.watch(config.sassPath + '/*.scss', ['css']);
  gulp.watch([config.jsPath + '/*.js', '!' + config.jsPath + '/*.min.js'], ['js']);
});


// Default task
gulp.task('default', ['css', 'js']);
