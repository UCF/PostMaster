(function () {
  function toggleEmptyMsg($row) {
    if (!$row.length) {
      return;
    }

    const $emptyMsg = $(`#${$row.data('empty-msg')}`);
    if ($emptyMsg.length) {
      if ($(`[class="${$row.attr('class')}"]:visible`).length) {
        $emptyMsg.addClass('d-none');
      } else {
        $emptyMsg.removeClass('d-none');
      }
    }
  }

  toggleEmptyMsg($('.js-ruleset-include:visible').first());
  toggleEmptyMsg($('.js-ruleset-exclude:visible').first());

  $('.js-ruleset').formset({
    prefix: $(this).data('prefix'), // The form prefix for your django formset
    addText: '<span class="fas fa-plus mr-1" aria-hidden="true"></span>Add Rule', // Text for the add link
    deleteText: '&times;<span class="sr-only">Remove Rule</span>', // Text for the delete link
    addContainerClass: null, // Container CSS class for the add link
    deleteContainerClass: 'js-ruleset-remove-container', // Container CSS class for the delete link. TODO this doesn't work
    addCssClass: 'btn btn-sm btn-default px-3', // CSS class applied to the add link
    deleteCssClass: 'close', // CSS class applied to the delete link
    added: toggleEmptyMsg,
    removed: toggleEmptyMsg
  });

  // TODO add sorting/re-ordering of rule rows
}());
