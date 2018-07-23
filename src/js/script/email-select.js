(function() {
  'use strict';

  var $viewEmailTrigger,
      $templates,
      $modalTrigger,
      inputId;

  function viewEmail(e) {
    e.preventDefault();
    var inputValue = $('#' + $(e.target).attr('data-id')).val();

    if(inputValue.startsWith('https://')) {
      window.open(inputValue, "_blank");
    }
  }

  function toggleEmailTrigger(e) {
    var $trigger = $('.' + $(e.target).attr('id'));
    if($(e.target).val().startsWith('https://')) {
      $trigger.fadeIn();
    } else {
      $trigger.fadeOut();
    }
  }

  function setInputId(e) {
    inputId = $(e.target).attr('data-id');
  }

  function copyEmailLink(e) {
    $('#' + inputId ).val($(e.target).attr('data-url')).blur();
    $('#viewUploadModal').modal('toggle');
  }

  function init() {
    $viewEmailTrigger = $('.view-email-trigger');
    $modalTrigger = $('.modal-trigger');
    $templates = $('.templates');

    // Add event handlers
    $('#id_source_html_uri, #id_source_text_uri').on('change, blur', toggleEmailTrigger).blur();
    $viewEmailTrigger.on('click', viewEmail);
    $modalTrigger.on('click', setInputId);
    $templates.on('click', copyEmailLink);
  }

  if($('#id_source_html_uri').length) {
    $(init);
  }

}());

