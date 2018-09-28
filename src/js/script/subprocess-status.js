(function() {
  'use strict';

  var JSON_URL = '/subprocess/json/?pk=',
    id,
    intervalId,
    $progressBar,
    $badge,
    $completed,
    $actionBtn,
    $error;

  function getProgress() {
    $.ajax({
      url: JSON_URL + id
    }).done(function (data) {
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

      if (data.status === 'Completed') {
        updateStatus(
          'info',
          'success',
          data.status,
          ''
        );

        $actionBtn
          .addClass('btn-success')
          .removeClass('d-none')
          .text('View Group')
          .attr('href', data.success_url);
      }

      if (data.status === 'Error') {
        updateStatus(
          'info',
          'danger',
          'Error',
          'Error: ' + data.error
        );

        $actionBtn
          .addClass('btn-danger')
          .removeClass('d-none')
          .text('Back to Import')
          .attr('href', data.success_url);
      }
    }).fail(function () {
      clearInterval(intervalId);
      $progressBar
        .parents('.alert')
        .text('Error retrieving subprocess status data.');
    });
  }

  function updateStatus(themeBefore, themeAfter, badgeText, message) {
    clearInterval(intervalId);

    // Update progress bar styles
    $progressBar
      .parents('.alert')
      .removeClass('alert-' + themeBefore)
      .addClass('alert-' + themeAfter);

    $error
      .text(message);

    $badge
      .removeClass('badge-' + themeBefore)
      .addClass('badge-' + themeAfter)
      .text(badgeText);
  }

  function init() {
    if (typeof POSTMASTER_SUBPROCESS === 'undefined') {
      return;
    }

    $progressBar = $('.progress-bar');
    $completed = $('.completed');
    $badge = $('.badge');
    $error = $('.error-text');
    $actionBtn = $('#action-button');
    id = POSTMASTER_SUBPROCESS.id;
    if ($progressBar.length) {
      intervalId = setInterval(getProgress, 2000);
    }
  }

  $(init);
}());
