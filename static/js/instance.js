(function () {
  'use strict';

  var JSON_URL = '/instance/json/?pk=',
    cancel_url,
    id,
    intervalId,
    $progressBar,
    $sent,
    $cancel_button,
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
    $cancel_button = $('.cancel-instance-btn');
    $.ajax({
      url: cancel_url,
      data: { pk: id }
    }).success(function (data) {
      console.log('instance has been cancelled');
      console.log(data);
      $cancel_button.children('.text').text('Cancelling Instance...');
      console.log($cancel_button.children('.hidden'));
      $cancel_button.children('.hidden').removeClass('hidden');
    }).error(function (data, statusText, xhr) {
      console.log('error');
      console.log(data);
      console.log(data.status);
    });
  }

  function init() {
    id = $('input.email-instance-id').val();
    $progressBar = $('.progress-bar');
    if ($progressBar.length) {
      $sent = $('.sent');
      intervalId = setInterval(getProgress, 2000);
    }

    $('.cancel-instance-form').on('click', '.cancel-instance-btn', function(e) {
      e.preventDefault();
      console.log('cancel the emails');
      cancel_url = '/email/instance/' + id + '/cancel';
      console.log(cancel_url);
      cancelInstance(cancel_url);
    });
  }

  $(init);

} ());
