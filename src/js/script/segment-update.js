/* global SEGMENT_INCLUDE_RULES_PREFIX, SEGMENT_EXCLUDE_RULES_PREFIX */
(function () {
  //
  // Show/hide empty message when a ruleset has no rules
  //
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

  function resetRowIndexes($target) {
    const nameRegex = /([A-Za-z\-_]+)\d+([A-Za-z\-_]+)/i;

    $.each($target.find('.js-ruleset:not([style*="display: none"])'), (idx, el) => {
      $(el).find('label').each((_, label) => {
        const $label = $(label);
        const attrFor = $label.attr('for')
          .replace(nameRegex, `$1${idx}$2`);
        $label.attr('for', attrFor);
      });

      $(el).find('select, input').each((_, control) => {
        const $control = $(control);
        const id = $control.attr('id')
          .replace(nameRegex, `$1${idx}$2`);
        const name = $control.attr('name')
          .replace(nameRegex, `$1${idx}$2`);
        $control.attr('id', id).attr('name', name);
      });
    });
  }

  const rulesetArgs = {
    addText: '<span class="fas fa-plus mr-1" aria-hidden="true"></span>Add Rule', // Text for the add link
    deleteText: '&times;<span class="sr-only">Remove Rule</span>', // Text for the delete link
    addContainerClass: null, // Container CSS class for the add link
    deleteContainerClass: 'js-ruleset-remove-container', // Container CSS class for the delete link.
    addCssClass: 'btn btn-sm btn-default px-3', // CSS class applied to the add link
    deleteCssClass: 'close ml-0', // CSS class applied to the delete link
    added: toggleEmptyMsg,
    removed: toggleEmptyMsg,
    hideLastAddForm: true
  };
  const includeRulesetArgs = $.extend({}, rulesetArgs, {
    prefix: SEGMENT_INCLUDE_RULES_PREFIX,
    formCssClass: 'js-ruleset-include'
  });
  const excludeRulesetArgs = $.extend({}, rulesetArgs, {
    prefix: SEGMENT_EXCLUDE_RULES_PREFIX,
    formCssClass: 'js-ruleset-exclude'
  });

  $('.js-ruleset-include').formset(includeRulesetArgs);
  $('.js-ruleset-exclude').formset(excludeRulesetArgs);

  toggleEmptyMsg($('.js-ruleset-include:visible').first());
  toggleEmptyMsg($('.js-ruleset-exclude:visible').first());

  //
  // TODO add sorting/re-ordering of rule rows
  //
  $('.js-rules-list').sortable({
    items: '.js-ruleset',
    handle: '.js-ruleset-grip',
    update: function (evt) {
      resetRowIndexes($(evt.target));
    }
  });
}());
