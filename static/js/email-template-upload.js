(function() {
  'use strict';

  var $viewEmailTrigger,
      $templates,
      $modalTrigger,
      inputId;

  function viewEmailTemplate(e) {
    e.preventDefault();
    var inputValue = $('#' + $(e.target).attr('data-id')).val();

    if(inputValue.startsWith('https://')) {
      window.open(inputValue, "_blank");
    }
  }

  function toggleEmailTrigger(e) {
    var $trigger = $(e.target).next().children('.view-email-trigger');
    if($(e.target).val().startsWith('https://')) {
      $trigger.fadeIn();
    } else {
      $trigger.fadeOut();
    }
  }

  function setInputId(e) {
    inputId = $(e.target).attr('data-id');
  }

  function copyTemplateLink(e) {
    $('#' + inputId ).val($(e.target).attr('data-url')).blur();
    $('#viewUploadModal').modal('toggle');
  }

  function init() {
    $viewEmailTrigger = $('.view-email-trigger');
    $modalTrigger = $('.modal-trigger');
    $templates = $('.templates');

    // Add event handlers
    if($viewEmailTrigger.length) {
      $viewEmailTrigger.parent().prev().on('change, blur', toggleEmailTrigger).blur();
      $viewEmailTrigger.on('click', viewEmailTemplate);
      $modalTrigger.on('click', setInputId);
      $templates.on('click', copyTemplateLink);
    }
  }

  $(init);

}());
