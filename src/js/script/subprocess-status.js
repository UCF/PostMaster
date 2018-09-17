(function() {
  'use strict';

  var JSON_URL = '/subprocess/json/?pk=',
    id,
    intervalId,
    $progressBar,
    $badge,
    $completed,
    error = false;

  function getProgress() {
    if (error) {
      clearInterval(intervalId);
      $progressBar
        .parents('.alert')
        .removeClass('alert-info')
        .addClass('alert-danger');
      $progressBar
        .parent()
        .replaceWith('<strong>Error: The subprocess has failed.');
      $badge
        .removeClass('badge-info')
        .addClass('badge-error')
        .text('Error');
    } else {
      $.ajax({
        url: JSON_URL + id
      }).done(function (data) {
        if (data.status === 'Completed') {
          clearInterval(intervalId);
          $progressBar
            .parents('.alert')
            .removeClass('alert-info')
            .addClass('alert-success');
          $badge
            .removeClass('badge-info')
            .addClass('badge-success')
            .text('Completed');

            return;
        }

        if (data.status === 'Error') {
          clearInterval(intervalId);
          $progressBar
            .parents('.alert')
            .removeClass('alert-info')
            .addClass('alert-danger');
          $progressBar
            .parent()
            .replaceWith('<p>Error: ' + data.error + '</p>');
          $badge
            .removeClass('badge-info')
            .addClass('badge-danger')
            .text('Error');
        }

        var percentage = Math.round(data.current_unit / data.total_units * 100);
        if (typeof percentage === 'number') {
          percentage = percentage + '%';
        } else {
          percentage = '0%';
        }

        $progressBar
          .css('width', percentage)
          .text(percentage);
        $completed
          .text(data.current_unit + ' of ' + data.total_units);
      }).fail(function () {
        clearInterval(intervalId);
        $progressBar
          .parents('.alert')
          .text('Error retrieving subprocess status data.');
      });
    }
  }

  function init() {
    if (typeof POSTMASTER_SUBPROCESS === 'undefined') {
      return;
    }

    $progressBar = $('.progress-bar');
    $completed = $('.completed');
    $badge = $('.badge');
    id = POSTMASTER_SUBPROCESS.id;
    if ($progressBar.length) {
      intervalId = setInterval(getProgress, 2000);
    }
  }

  $(init);
}());
