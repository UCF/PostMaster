(function () {
  'use strict';

  var JSON_URL = '/instance/json/?pk=',
    cancel_url,
    id,
    intervalId,
    $progressBar,
    $sent,
    $cancelForm,
    $cancelBtn,
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
      $cancelForm.slideUp();
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

  function cancelButtonHandler() {
    if ($cancelBtn.hasClass('open-instance-page')) {
      window.location = INSTANCE_URL + id + '#check_on_load';
    }
    else {
      id = $cancelBtn.parent('.cancel-instance-form').children('input.email-instance-id').val();
      cancel_url = '/email/instance/' + id + '/cancel/';
      cancelInstance(cancel_url, $cancelBtn);
    }
  }

  function cancelInstance(cancel_url) {
    $.ajax({
      url: cancel_url,
      data: { pk: id }
    }).success(function (data) {
      $cancelBtn.children('.text').text('Cancelling Instance...');
      $cancelBtn.children('.hidden').removeClass('hidden');
    }).error(function (data, statusText, xhr) {
      console.log('error');
      console.log(data);
    });
  }

  function init() {
    var current_hash = window.location.hash.replace('#', '');
    $cancelForm = $('.cancel-instance-form');
    $progressBar = $('.progress-bar');
    $cancelBtn = $('.cancel-instance-btn');

    if (current_hash == 'check_on_load' && $cancelBtn.length > 0) {
      cancelButtonHandler();
    }

    id = $('input.email-instance-id').val();
    if ($progressBar.length) {
      $sent = $('.sent');
      intervalId = setInterval(getProgress, 2000);
    }

    $cancelForm.on('click', '.cancel-instance-btn', function(e) {
      e.preventDefault();
      cancel_url = '/email/instance/' + id + '/cancel';
      cancelInstance(cancel_url);
    });
  }

  $(init);

} ());
