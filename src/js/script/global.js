(function() {
  'use strict';

  function tableClickHandler(e) {
    var location = $(e.target).parent().attr('data-link-url');
    if (location) {
      window.location = location;
    }
  }

  function formValidation() {
    $('input').on('blur', function() {
      if($(this).attr('required') && !$(this).hasClass('search-query')) {
        if($(this).val()) {
          $(this).parents('.form-group').removeClass('has-danger').addClass('has-success');
        } else {
          $(this).parents('.form-group').removeClass('has-success').addClass('has-danger');
        }
      }
    });
    $('select').on('blur', function() {
      if($(this).attr('required')) {
        if($(this).val().length) {
          $(this).parents('.form-group').removeClass('has-danger').addClass('has-success');
        } else {
          $(this).parents('.form-group').removeClass('has-success').addClass('has-danger');
        }
      }
    });
  }

  function select2TemplateResult(result) {
    return $('<span><span class="select2-option-icon mr-3" aria-hidden="true"></span><span class="select2-option-text">' + result.text + '</span></span>');
  }

  function init() {
    // Table row click handler
    $('table').on('click', 'td:not(:has(a))', tableClickHandler);
    // initiate tooltip
    $('[data-toggle="tooltip"]').tooltip();
    // Initiate select2 on multi-select inputs
    $('select[multiple]').select2({
      templateResult: select2TemplateResult,
      closeOnSelect: false
    });
    // Initiate datepickers
    $('input[data-datepicker]').each(function() {
      var $datepicker = $(this);
      $datepicker.pikaday({
        format: 'MM/DD/YYYY'
      });
    });
    // Initiate timepickers
    $('input[data-timepicker]').timepicker({
      'scrollDefault': 'now',
      'timeFormat': 'h:i a',
      'step': 15
    });
    formValidation();
  }

  $(init);

}());
