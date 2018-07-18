(function() {
  'use strict';

  var $viewEmailTrigger;

  function viewEmailTemplate(e) {
    e.preventDefault();
    var inputValue = $(e.target).parent().prev().val();

    if(inputValue.startsWith('https://')) {
      window.open(inputValue, "_blank");
    }
  }

  function toggleEmailTrigger(e) {
    var $trigger = $(e.target).next().children();
    if($(e.target).val().startsWith('https://')) {
      $trigger.fadeIn();
    } else {
      $trigger.fadeOut();
    }
  }

  function init() {
    $viewEmailTrigger = $('.view-email-trigger');

    // Add event handlers
    if($viewEmailTrigger.length) {
      $viewEmailTrigger.parent().prev().on('change', toggleEmailTrigger).change();
      $viewEmailTrigger.on('click', viewEmailTemplate);
    }
  }

  $(init);

}());
