(function() {
  'use strict';

  function tableClickHandler(e) {
    var location = $(e.target).parent().attr('data-link-url');
    if (location) {
      window.location = location;
    }
  }

  function init() {
    // Table row click handler
    $('table').on('click', 'td:not(:has(a))', tableClickHandler);
    // Select the first form input
    $('form:first *:input[type!=hidden]:input[type!=checkbox]:first').focus();
  }

  $(init);

}());