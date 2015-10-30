var gulp = require('gulp'),
    config = require('./config.json'),
    sass = require('gulp-sass'),
    minifyCss = require('gulp-minify-css'),
    bless = require('gulp-bless'),
    notify = require('gulp-notify'),
    bower = require('gulp-bower'),
    concat = require('gulp-concat'),
    uglify = require('gulp-uglify'),
    prefix = require('gulp-autoprefixer'),
    rename = require('gulp-rename'),
    jshint = require('gulp-jshint'),
    jshintStylish = require('jshint-stylish'),
    scsslint = require('gulp-scss-lint'),
    vinylPaths = require('vinyl-paths'),
    browserSync = require('browser-sync').create(),
    reload = browserSync.reload;

var config = {
  sassPath: './static/scss',
  cssPath: './static/css',
  jsPath: './static/js',
  fontPath: './static/fonts',
  htmlPath: './',
  bowerDir: './static/bower_components',
  sync: config.sync,
  target: config.target,
};


// Run Bower
gulp.task('bower', function() {
  return bower()
    .pipe(gulp.dest(config.bowerDir))
    .on('end', function() {
      // Add Glyphicons fonts
      gulp.src(config.bowerDir + '/bootstrap-sass-official/assets/fonts/*/*')
        .pipe(gulp.dest(config.fontPath));
    });
});


// Process .scss files in /static/scss/
gulp.task('css', function() {
  return gulp.src(config.sassPath + '/*.scss')
    .pipe(scsslint({
      'config': 'scss-lint-config.yml',
    }))
    .pipe(sass().on('error', sass.logError))
    .pipe(prefix({
        browsers: ["last 3 versions", "> 10%", "ie 8"],
        cascade: false
    }))
    .pipe(minifyCss({compatibility: 'ie8'}))
    .pipe(rename('style.min.css'))
    .pipe(bless())
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
        config.bowerDir + '/jquery/dist/jquery.js',
        config.bowerDir + '/bootstrap-sass-official/assets/javascripts/bootstrap.js',
        config.bowerDir + '/typeahead.js/dist/typeahead.bundle.js',
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
gulp.task('default', ['bower', 'css', 'js']);