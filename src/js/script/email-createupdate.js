(function() {
  'use strict';

  var $uploadModalTriggers,
      $uploadModal,
      $uploadModalFileInput,
      $uploadModalSubmitBtn,
      $viewEmailTriggers,
      $emailSelectInputs;


  //
  // Performs setup steps for whenever the email upload modal is opened
  //
  function setupUploadModal(e) {
    var $toggleBtn = $(e.target);
    var formFieldID = $toggleBtn.attr('data-id');
    var inputAccepts = $toggleBtn.attr('data-accept');

    // Add the 'accept' attr to the file upload input. Unset any existing value
    // on the upload input
    $uploadModalFileInput
      .attr('accept', inputAccepts)
      .val('')
      .trigger('change');

    // Add the 'data-insert-field' attr to the submit btn for reference later
    $uploadModalSubmitBtn.attr('data-insert-field', formFieldID);
  }

  //
  // Toggles the email upload modal's submit button state depending on if
  // a file has been selected yet
  //
  function toggleSubmitBtnState() {
    if ($uploadModalFileInput.val()) {
      $uploadModalSubmitBtn.removeAttr('disabled');
    }
    else {
      $uploadModalSubmitBtn.attr('disabled', 'disabled');
    }
  }

  //
  // Cleans a string suitable for use as a filename
  //
  function cleanFilename(filename, ext) {
    filename = $.trim(filename).replace(/[^a-z0-9-_]/gi, '-').replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 100);
    if (filename.substr(filename.length - (ext.length + 1)) !== '.' + ext) {
      filename += '.' + ext;
    }
    return filename;
  }

  //
  // Handles uploading a selected file in the email upload modal and passing
  // the newly-uploaded file's uri to the corresponding form field
  //
  function processUploadedEmailFile() {
    var fileRaw = $uploadModalFileInput.prop('files')[0];
    if (!fileRaw || $uploadModalSubmitBtn.attr('disabled')) { return; }

    // Set up uploaded file data
    var ext = '';
    var extGroupname = '';
    if ($uploadModalFileInput.attr('accept') === 'text/html') {
      ext = 'html';
      extGroupname = 'html';
    }
    else {
      ext = 'txt';
      extGroupname = 'plaintext';
    }
    var filename = cleanFilename(fileRaw.name, ext);
    var fileFormData = new FormData();
    fileFormData.append('file', fileRaw, filename);
    fileFormData.append('extension_groupname', extGroupname);
    fileFormData.append('protocol', 'https://');
    fileFormData.append('unique', true); // force unique filenames to prevent overridden files

    // Ajax submit to file upload view
    $.when(
      $.ajax({
        cache: false,
        contentType: false,
        data: fileFormData,
        dataType: 'json',
        method: 'POST',
        processData: false,
        url: $uploadModalSubmitBtn.attr('data-upload-action')
      })
    )
      .done(function (fileArgs) {
        if (Array.isArray(fileArgs)) {
          fileArgs = fileArgs[0];
        }
        var fileURI = fileArgs.link;
        var $insertField = $('#' + $uploadModalSubmitBtn.attr('data-insert-field'));
        $insertField
          .val(fileURI)
          .trigger('blur');

        // Finally, close the modal
        $uploadModal.modal('hide');
      })
      .fail(function (result) {
        // TODO
        console.log(result);
      });
  }

  //
  // Show/hide the 'View Email' buttons based on associated input value
  //
  function toggleEmailTrigger(e) {
    var $selectInput = $(e.target);
    var $trigger = $viewEmailTriggers.filter('[data-id="' + $selectInput.attr('id') +'"]');
    if ($selectInput.val().startsWith('https://')) {
      $trigger.removeClass('d-none');
    } else {
      $trigger.addClass('d-none');
    }
  }

  //
  // Opens a selected email file in a new tab
  //
  function viewEmail(e) {
    e.preventDefault();
    var inputValue = $('#' + $(e.target).attr('data-id')).val();
    if (inputValue.startsWith('https://')) {
      window.open(inputValue, '_blank');
    }
  }

  function init() {
    $uploadModalTriggers = $('.upload-modal-trigger');
    $uploadModal = $('#upload-email-modal');
    $uploadModalFileInput = $uploadModal.find('#upload-email-file-input');
    $uploadModalSubmitBtn = $uploadModal.find('#upload-email-submit');
    $viewEmailTriggers = $('.view-email-trigger');
    $emailSelectInputs = $('#id_source_html_uri, #id_source_text_uri');

    $uploadModalTriggers.on('click', setupUploadModal);
    $uploadModalFileInput.on('change', toggleSubmitBtnState);
    $uploadModalSubmitBtn.on('click', processUploadedEmailFile);
    $emailSelectInputs.on('change blur', toggleEmailTrigger).blur();
    $viewEmailTriggers.on('click', viewEmail);
  }

  $(init);

}());

