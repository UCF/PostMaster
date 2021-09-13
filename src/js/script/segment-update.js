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

  //
  // Finds all rows in the given parent $target and
  // resets label, input ID indexes
  //
  function resetRowIndexes($target) {
    const nameRegex = /([A-Za-z\-_]+)\d+([A-Za-z\-_]+)/i;

    $.each($target.find('.ruleset:not([style*="display: none"])'), (idx, el) => {
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

  //
  // Applies event handlers and such to new rows
  //
  function rowInit($row) {
    // const $container = $row.parent('.rules-list');
    $row.find('.rule-control-key, .rule-control-value').hide();
    $row.find('.rule-control-field').on('change', handleFieldInputChange);
  }

  //
  // Handle when a new row is added
  //
  function handleRowAdd($row) {
    toggleEmptyMsg($row);
    rowInit($row);
  }

  //
  // Handle when a row is deleted
  //
  function handleRowDelete($row) {
    toggleEmptyMsg($row);
  }

  //
  // Handle when a field input's value changes
  //
  function handleFieldInputChange(e) {
    const $input = $(e.target);
    const $row = $input.parents('.ruleset');
    const $keyCol = $row.find('.rule-group-key');
    const $valCol = $row.find('.rule-group-value');

    $keyCol.empty();
    $valCol.empty();

    switch ($input.val()) {
      // TODO there is probably a better way of defining
      // how to transform these inputs in the template
      case 'in_recipient_group':
        // TODO init selectjs of searchable RecipientGroups on Key
        $('<div>TODO</div>').appendTo($keyCol);
        break;
      case 'has_attribute':
        // TODO init selectjs of searchable RecipientAttributes on Key; show Value text input
        $('<div>TODO</div>').appendTo($keyCol);
        $('<div>TODO</div>').appendTo($valCol);
        break;
      case 'received_instance':
      case 'opened_instance':
      case 'clicked_any_url_in_email':
        // TODO init selectjs of searchable Instances on Key
        $('<div>TODO</div>').appendTo($keyCol);
        break;
      case 'opened_email':
        // TODO init selectjs of searchable Emails on Key
        $('<div>TODO</div>').appendTo($keyCol);
        break;
      case 'clicked_link':
        // TODO basic text inputs for Key and Value
        $('<div>TODO</div>').appendTo($keyCol);
        $('<div>TODO</div>').appendTo($valCol);
        break;
      case 'clicked_url_in_instance':
        // TODO basic text input for Key; init selectjs of searchable Instances on Value
        $('<div>TODO</div>').appendTo($keyCol);
        $('<div>TODO</div>').appendTo($valCol);
        break;
      default:
        break;
    }
  }

  //
  // Initialize row add/remove logic
  //
  const rulesetArgs = {
    addText: '<span class="fas fa-plus mr-1" aria-hidden="true"></span>Add Rule', // Text for the add link
    deleteText: '&times;<span class="sr-only">Remove Rule</span>', // Text for the delete link
    addContainerClass: null, // Container CSS class for the add link
    deleteContainerClass: 'ruleset-remove-container', // Container CSS class for the delete link.
    addCssClass: 'btn btn-sm btn-default px-3', // CSS class applied to the add link
    deleteCssClass: 'close ml-0', // CSS class applied to the delete link
    added: handleRowAdd,
    removed: handleRowDelete,
    hideLastAddForm: true
  };
  const includeRulesetArgs = $.extend({}, rulesetArgs, {
    prefix: SEGMENT_INCLUDE_RULES_PREFIX,
    formCssClass: 'ruleset-include'
  });
  const excludeRulesetArgs = $.extend({}, rulesetArgs, {
    prefix: SEGMENT_EXCLUDE_RULES_PREFIX,
    formCssClass: 'ruleset-exclude'
  });

  $('.ruleset-include').formset(includeRulesetArgs);
  $('.ruleset-exclude').formset(excludeRulesetArgs);
  $('.ruleset').each(function() {
    rowInit($(this));
  });

  toggleEmptyMsg($('.ruleset-include:visible').first());
  toggleEmptyMsg($('.ruleset-exclude:visible').first());

  //
  // Initialize drag-and-drop and sorting of rows
  //
  $('.rules-list').sortable({
    items: '.ruleset',
    handle: '.ruleset-grip',
    update: function (evt) {
      resetRowIndexes($(evt.target));
    }
  });
}());
