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
      if($(this).attr('required')) {
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

  function init() {
    // Table row click handler
    $('table').on('click', 'td:not(:has(a))', tableClickHandler);
    // initiate tooltip
    $('[data-toggle="tooltip"]').tooltip();
    formValidation();
  }

  $(init);

}());
