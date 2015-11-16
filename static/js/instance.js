(function () {
  'use strict';

  var PROGRESS_INSTANCE_URL = '/instance/json/?pk=',
    CANCEL_INSTANCE_URL = '/email/instance/!@!/cancel',
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
        url: PROGRESS_INSTANCE_URL,
        data: { pk: id }
      }).done(function (data) {
        if (data.end) {
          location.reload();
        } else {
          if(new Date() - new Date(data.start) > ONE_DAY) {
            error = true;
          } else {
            var percentage = Math.round(data.sent_count / data.total * 100) + '%';
            $progressBar
              .css('width', percentage)
              .text(percentage);
            $sent.text(data.sent_count + ' of ' + data.total);
          }
        }
      });
    }
  }

  function cancelInstance(cancel_url) {
    $.ajax({
      url: cancel_url,
      data: { pk: id }
    }).success(function (data) {
      console.log('instance has been cancelled');
      console.log(data);
    }).error(function (data, statusText, xhr) {
      console.log('error');
      console.log(data);
      console.log(data.status);
    });
  }

  function init() {
    $progressBar = $('.progress-bar');
    if ($progressBar.length) {
      id = $progressBar.attr('data-id');
      $sent = $('.sent');
      intervalId = setInterval(getProgress, 2000);
    }

    var $cancel = $('.cancel-instance-form');
    $cancel.on('click', '.cancel-instance-btn', function(e) {
      e.preventDefault();
      console.log('cancel the emails');
      var cancel_url = CANCEL_INSTANCE_URL.replace('!@!', id);
      console.log(cancel_url);
      cancelInstance(cancel_url);
    });
  }

  $(init);

} ());
