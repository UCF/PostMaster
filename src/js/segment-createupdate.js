/* global SEGMENT_INCLUDE_RULES_PREFIX, SEGMENT_EXCLUDE_RULES_PREFIX */

// Dynamic formsets
// =require jquery.formset/src/jquery.formset.js

// jQuery UI - Sortable
// =require jquery-ui-sortable/jquery-ui.min.js


(function () {
  const nameRegex = /([A-Za-z\-_]+)(\d+)([A-Za-z\-_]+)/i;

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
  function resetRowIndexes($row, idx) {
    $row.find('label').each((_, label) => {
      const $label = $(label);
      let attrFor = $label.attr('for');
      if (attrFor) {
        attrFor = attrFor.replace(nameRegex, `$1${idx}$3`);
        $label.attr('for', attrFor);
      }
    });

    $row.find('select, input').each((_, control) => {
      const $control = $(control);

      let id = $control.attr('id');
      if (id) {
        id = id.replace(nameRegex, `$1${idx}$3`);
        $control.attr('id', id);
      }

      let name = $control.attr('name');
      if (name) {
        name = name.replace(nameRegex, `$1${idx}$3`);
        $control.attr('name', name);
      }
    });

    $row.find('.rule-conditional-input-container').each((_, container) => {
      const $container = $(container);
      let dataControls = $container.attr('data-controls');
      if (dataControls) {
        dataControls = dataControls.replace(nameRegex, `$1${idx}$3`);
      }
      $container.attr('data-controls', dataControls);
    });
  }

  //
  // Applies event handlers and such to new rows
  //
  function rowInit($row) {
    const fieldVal = $row.find('.rule-control-field').val();

    // Hide all conditional inputs:
    $row
      .find('.rule-conditional-input-container')
      .hide();

    // Initialize conditional inputs if `field` is set
    // (e.g. if this is a ruleset for an existing Segment):
    if (fieldVal) {
      const $toggleableInputs = $row.find(`.rule-conditional-input-container[data-field-values*="${fieldVal}"]`);
      $toggleableInputs.each(function () {
        conditionalInputInit($(this));
      });
    }

    // Assign event handler to `field`:
    $row
      .find('.rule-control-field')
      .on('change', handleFieldInputChange);
  }

  //
  // Handle when a new row is added
  //
  function handleRowAdd($row) {
    toggleEmptyMsg($row);
    rowInit($row);

    // TODO this winds up doing some redundant logic.
    // Consider splitting out `.rule-conditional-input-container`
    // data-controls attr updates into a separate function
    const fieldID = $row.find('.rule-control-field').attr('id');
    const idx = fieldID.match(nameRegex)[2] || null;
    if (idx) {
      resetRowIndexes($row, idx);
    }
  }

  //
  // Handle when a row is deleted
  //
  function handleRowDelete($row) {
    toggleEmptyMsg($row);
  }

  //
  // Initializes a conditional key/value input
  //
  function conditionalInputInit($inputContainer) {
    const inputType = $inputContainer.data('inputType');
    const initialized = $inputContainer.data('inputInitialized');

    if (initialized !== 'true') {
      const $controlledInput = $(`#${$inputContainer.data('controls')}`);

      // Generate a "unique" ID for the new input
      // and for its label to reference
      const inputID = `rule-input-${Math.floor(Math.random() * (999999999 - 1) + 1)}`;

      // Update for attr on label
      const $label = $inputContainer.find('label');
      $label.attr('for', inputID);

      // Create + insert input
      let $input = null;
      switch (inputType) {
        case 'select2':
          $input = $inputContainer.find('select');
          $input.select2({
            ajax: {
              url: $inputContainer.data('optionsEndpoint'),
              dataType: 'json'
            }
          });
          break;
        case 'text':
          $input = $inputContainer.find('input[type="text"]');
          break;
        default:
          break;
      }
      $input
        .attr('id', inputID)
        .val($controlledInput.val()) // set initial input value based on controlled input
        .trigger('change') // required for select2 inputs
        .on('change', function () {
          $controlledInput.val($(this).val());
        })
        .appendTo($inputContainer);

      // Flag input as "initialized"
      $inputContainer.data('inputInitialized', 'true');
    }

    // Finally, display the input
    $inputContainer.show();
  }

  //
  // Handle when a field input's value changes
  //
  function handleFieldInputChange(e) {
    const $input = $(e.target);
    const $row = $input.parents('.ruleset');
    const fieldVal = $input.val();

    // Hide all conditional inputs, and clear their values:
    $row
      .find('.rule-conditional-input-container')
      .hide()
      .find('.rule-conditional-input')
      .val('')
      .trigger('change');

    // Clear hidden key/value inputs:
    $row.find('.rule-controlled-input').val('');

    const $toggledInputs = $row.find(`.rule-conditional-input-container[data-field-values*="${fieldVal}"]`);
    $toggledInputs.each(function () {
      conditionalInputInit($(this));
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
    hideLastAddForm: false
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
    update: function (e) {
      const $list = $(e.target);
      $.each($list.find('.ruleset:visible'), (idx, el) => {
        const $row = $(el);
        resetRowIndexes($row, idx);
      });
    }
  });
}());
