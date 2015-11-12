(function () {
  'use strict';

  var JSON_URL = '/instance/json/?pk=',
    id,
    $progressBar,
    $sent;

  function getProgress() {
    $.ajax({
      url: JSON_URL,
      data: { pk: id }
    }).done(function (data) {
      if (data.sent_count === data.total) {
        location.reload();
      } else {
        var percentage = Math.round(data.sent_count / data.total * 100) + '%';
        $progressBar
          .css('width', percentage)
          .text(percentage);
        $sent.text(data.sent_count + ' of ' + data.total);
      }
    });
  }

  function init() {
    $progressBar = $('.progress-bar');

    if ($progressBar.length) {
      id = $progressBar.attr('data-id');
      $sent = $('.sent');
      setInterval(getProgress, 1000);
    }
  }

  $(init);

} ());
