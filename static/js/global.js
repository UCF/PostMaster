(function() {
  'use strict';

  function tableClickHandler(e) {
    window.location = $(e.target).parent().attr('data-link-url');
  }

  function init() {
    // Table row click handler
    $('table').on('click', 'td:not(:has(a))', tableClickHandler);
    // Select the first form input
    $('form:first *:input[type!=hidden]:input[type!=checkbox]:first').focus();
  }

  $(init);

}());
