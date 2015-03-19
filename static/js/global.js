(function() {
  'use strict';

  function tableClickHandler(e) {
    window.location = $(e.target).parent().attr('data-link-url');
  }

  function init() {
    $('table').on('click', 'td:not(:has(a))', tableClickHandler);
  }

  $(init);

}());
