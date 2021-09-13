/* global SEGMENT_INCLUDE_RULES_PREFIX, SEGMENT_EXCLUDE_RULES_PREFIX */

// Dynamic formsets
// =require jquery.formset/src/jquery.formset.js

// jQuery UI - Sortable
// =require jquery-ui-sortable/jquery-ui.min.js


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
    $row
      .find('.rule-control-field')
      .on('change', handleFieldInputChange)
      .trigger('change');
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
    const fieldVal = $input.val();

    // Hide all conditional inputs, and clear their values:
    $keyCol
      .find('.js-rule-conditional-input-container')
      .hide()
      .find('.js-rule-conditional-input')
      .val('');
    $valCol
      .find('.js-rule-conditional-input-container')
      .hide()
      .find('.js-rule-conditional-input')
      .val('');

    // Clear key/value inputs:
    $row.find('.js-rule-controlled-input').val('');

    const $toggledInputs = $row.find(`.js-rule-conditional-input-container[data-field-values*="${fieldVal}"]`);
    $toggledInputs.each(function () {
      const $toggledInput = $(this);
      const inputType = $toggledInput.data('inputType');
      const initialized = $toggledInput.data('inputInitialized');

      if (initialized !== 'true') {
        const $controlledInput = $(`#${$toggledInput.data('controls')}`);

        // Generate a "unique" ID for the new input
        // and for its label to reference
        const inputID = `js-rule-input-${Math.floor(Math.random() * (999999999 - 1) + 1)}`;

        // Update for attr on label
        const $label = $toggledInput.find('label');
        $label.attr('for', inputID);

        // Create + insert input
        let $input = null;
        switch (inputType) {
          case 'select2':
            $input = $toggledInput.find('select')
              .select2({
                // TODO this will need a callback for massaging incoming data
                ajax: {
                  url: $toggledInput.data('optionsEndpoint'),
                  dataType: 'json'
                }
              });
            break;
          case 'text':
            $input = $toggledInput.find('input[type="text"]');
            break;
          default:
            break;
        }
        $input
          .attr('id', inputID)
          .on('change', function () {
            $controlledInput.val($(this).val());
          })
          .appendTo($toggledInput);

        // Flag input as "initialized"
        $toggledInput.data('inputInitialized', 'true');
      }

      // Finally, display the input
      $toggledInput.show();
    });
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
  $('.ruleset').each(function () {
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
