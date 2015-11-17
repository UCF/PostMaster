(function () {
  'use strict';

  var JSON_URL = '/instance/json/?pk=',
    id,
    intervalId,
    $progressBar,
    $sent,
    error = false,
    ONE_DAY = 24 * 60 * 60 * 1000;

  function getProgress() {
    if (error) {
      clearInterval(intervalId);
      $progressBar
        .parents('.alert')
        .removeClass('alert-info')
        .addClass('alert-danger');
      $progressBar
        .parent()
        .replaceWith('<strong>Error: The email send may have failed, the start time is more than 24 hours ago.</strong>');
    } else {
      $.ajax({
        url: JSON_URL,
        data: { pk: id }
      }).done(function (data) {
        if (data.end) {
          window.location.reload();
        } else if (data.error) {
          $progressBar
            .parents('.alert')
            .text(data.error);
        } else {
          if (new Date() - new Date(data.start) > ONE_DAY) {
            error = true;
          } else {
            var percentage = Math.round(data.sent_count / data.total * 100) + '%';
            $progressBar
              .css('width', percentage)
              .text(percentage);
            $sent.text(data.sent_count + ' of ' + data.total);
          }
        }
      }).fail(function () {
        clearInterval(intervalId);
        $progressBar
          .parents('.alert')
          .text('Error retrieving sent email data.');
      });
    }
  }

  function init() {
    $progressBar = $('.progress-bar');
    if ($progressBar.length) {
      id = $progressBar.attr('data-id');
      $sent = $('.sent');
      intervalId = setInterval(getProgress, 2000);
    }
  }

  $(init);

} ());
