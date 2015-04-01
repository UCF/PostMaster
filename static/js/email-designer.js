// Loads a template (or snapshot) via ajax.
function loadTemplate(templateSrc) {
  var template = '';

  if (templateSrc === '') {
    loadEditor(template);
    return;
  }

  $.ajax({
    cache: false,
    dataType: 'html',
    method: 'GET',
    url: templateSrc
  })
    .done(function(data) {
      template = data;
      loadEditor(template);
    })
    .fail(function() {
      alert('Failed to load template or snapshot.');
    });
  return;
}


// Loads the editor window (appends template markup and editor scripts to the
// iframe source.)
function loadEditor(template) {
  var templateScripts = $('#editor-template-scripts').val();

  // Plain-jane string replacement to append editor scripts to the template
  if (template !== '') {
    template = template.replace('<div id="pm-editor-scripts"></div>', '<div id="pm-editor-scripts">' + templateScripts + '</div>');
  }

  // Add the combined template html + editor markup to the editor iframe
  var doc = document.getElementById('editor-window').contentWindow.document;
  doc.open();
  doc.write(''); // clear existing contents
  doc.write(template);
  doc.close();

  if (template === '') {
    // Disable save changes btn if editor window is empty
    $('#pre-save-changes').attr('disabled', 'disabled');
  }
  else {
    $('#pre-save-changes').removeAttr('disabled');
  }
}


// Appends a doctype to a string of markup.  Assumes the string does not
// already contain a doctype declaration.
function appendDoctypeToMarkup(markupString) {
  var docType = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">';
  return docType + markupString;
}


// Returns a string containing cleaned markup suitable for sending in an email.
// Assumes markupString does NOT contain a doctype declaration.
function getCleanedMarkupString(markupString, pPadding, pLineHeight, pFontFamily) {
  var parser = new DOMParser();
  var domDoc = parser.parseFromString(markupString, 'text/html');
  var $domDoc = $(domDoc);

  // Find the editor scripts we injected previously and remove them.
  // Make sure any potential leftover scripts/markup from Froala are removed
  // too.  (This requires #pm-editor-scripts to be the last element in the
  // template before the closing body tag.)
  $domDoc
    .find('#pm-editor-scripts')
      .nextAll()
      .addBack()
        .remove();

  // Find editable field that corresponds to the email's title; fill in <title> value
  var title = $domDoc.find('#pm-template-doctitle').text() || '';
  $domDoc.find('title').text(title);

  // Add inline line-height:inherit declaration to span's inside
  // .pm-template-editable-paragraph.
  // Make all images within paragraphs responsive; strip out remaining inline css.
  // Replace all .pm-template-editable-paragraph p tags with tables
  // (<p> tags are too inconsistent across email clients.)
  $domDoc
    .find('.pm-template-editable-paragraph p span')
      .css('line-height', 'inherit')
      .end()
    .find('.pm-template-editable-paragraph p')
      .find('img')
        .addClass('responsiveimg')
        .attr('style', '')
        .end()
      .wrap('<table class="paragraphtable" style="width: 100%;"><tr><td class="paragraphtd" style="width: 100%; font-family: '+ pFontFamily +'; padding: '+ pPadding +'; margin: 0; line-height: '+ pLineHeight +';"></td></tr></table>')
      .contents()
      .unwrap();

  // Unwrap/remove remaining .pm-template-editable-container's
  // (.pm-template-editable-paragraph's are removed above)
  $domDoc.find('.pm-template-editable-container').contents().unwrap();
  $domDoc.find('.pm-template-editable-container:empty').remove();

  // Make sure all image urls are absolute (http)
  $domDoc.find('body img').attr('src', function(index, val) {
    if (val.substring(0, 2) == '//') {
      val = val.replace('//', 'http://');
    }
    if (val.substring(0, 5) == 'https') {
      val = val.replace('https', 'http');
    }
    return val;
  });

  // Replace domDoc with the jquery object's reference of the element
  domDoc = $domDoc[0];

  // We can't access the iframe's doctype when we grab its contents, so re-add it here:
  var docMarkupClean = appendDoctypeToMarkup(domDoc.documentElement.outerHTML);

  return docMarkupClean;
}


// Retrieve existing snapshots
function getExistingSnapshots(getSnapshotsURL, $snapshotListItemMarkup) {
  var $snapshotList = $('#load-snapshot-list');

  // Clear existing value
  $snapshotList.html('');

  $.ajax({
    cache: false,
    data: {
      extension_groupname: 'html',
      protocol: '//'
    },
    dataType: 'json',
    method: 'GET',
    url: getSnapshotsURL
  })
    .done(function(data) {
      if (data.length > 0) {
        count = 0;
        $.each(data, function(index, snapshotURL) {
          // Check specifically for snapshots
          if (snapshotURL.substring(snapshotURL.length - 14) == '.snapshot.html') {
            $listItem = $snapshotListItemMarkup.clone();
            $listItem
              .find('input[type="radio"]')
                .val(snapshotURL)
                .end()
              .find('.snapshot-list-item-name')
                .text(snapshotURL);
            $snapshotList.append($listItem);
            count++;
          }
        });
        if (count === 0) {
          $snapshotList.html('No snapshots found.');
        }
      }
      else {
        $snapshotList.html('No snapshots found.');
      }
    })
    .fail(function() {
      $snapshotList.html('Could not load snapshot list.  Please try again later.');
    });
}


// Determines if a snapshot URL looks valid (came from our s3 instance).
// This won't actually check to see if the file exists at the given location,
// but makes sure we don't attempt to fetch something that doesn't look right
function snapshotURLIsValid(validKeyPath, snapshotURL) {
  var is_valid = false;

  if (snapshotURL.length && validKeyPath.length) {
    snapshotURL = $.trim(snapshotURL);
    snapshotURL = snapshotURL.replace(/^(https?:)?\/\//, '');
    validKeyPath = validKeyPath.replace(/^http:\/\//, ''); // http is forced, so expect it

    if (
      snapshotURL.slice(0, validKeyPath.length) == validKeyPath &&
      snapshotURL.slice(-14) == '.snapshot.html'
    ) {
      is_valid = true;
    }
  }

  return is_valid;
}


// Loads a snapshot from the snapshot select modal form
function loadSnapshot(validKeyPath) {
  var snapshotURL = '',
      $snapshotByURL = $('#load-snapshot-urlfield'),
      snapshotListVal = $('#load-snapshot-list').find('input[type="radio"]:checked').val(),
      snapshotByURLVal = $snapshotByURL.val();

  if (snapshotURLIsValid(validKeyPath, snapshotListVal)) {
    snapshotURL = snapshotListVal;
  }
  else if (snapshotURLIsValid(validKeyPath, snapshotByURLVal)) {
    snapshotURL = snapshotByURLVal;
  }

  if (snapshotURL) {
    // Ensure returned url is protocol relative
    snapshotURL = snapshotURL.replace(/^https?:\/\//, '//');
    if (snapshotURL.slice(0, 2) !== '//') {
      snapshotURL = '//' + snapshotURL;
    }

    loadTemplate(snapshotURL);

    // Manually close modal--the load snapshot submit button does not do this
    // automatically, since we need to validate first
    $('#load-snapshot-modal').modal('hide');

    // Reset template dropdown
    $('#template-select').val('');
  }
  else {
    alert('Could not load snapshot: snapshot is invalid.');
  }
}


// Returns Blob object containing markup for snapshot
function getSnapshotMarkup() {
  // var editorWindow = document.getElementById('editor-window').contentWindow;
  var editorWindow = $('#editor-window')[0].contentWindow;

  // Stop here if the editor window doesn't exist (should never reach this
  // point, but just in case)
  if (!editorWindow) {
    return;
  }

  // Destroy all active Froala editors in the iframe to remove Froala markup
  editorWindow.pmDesignerDestroy();

  // Grab the editor's markup as a string.  Just re-add the doctype for snapshots.
  var docMarkup = editorWindow.document.documentElement.outerHTML;
  docMarkup = appendDoctypeToMarkup(docMarkup);

  // Reload the editors
  editorWindow.pmDesignerEnable();

  return docMarkup;
}


// Returns Blob object containing markup for cleaned, live-ready email
function getLiveHTMLMarkup() {
  // var editorWindow = document.getElementById('editor-window').contentWindow;
  var editorWindow = $('#editor-window')[0].contentWindow;

  // Stop here if the editor window doesn't exist (should never reach this
  // point, but just in case)
  if (!editorWindow) {
    return;
  }

  // Destroy all active Froala editors in the iframe to remove Froala markup
  editorWindow.pmDesignerDestroy();

  // Fetch necessary css styles from the editor window for generating
  // email-friendly markup and inline styles
  var pPadding = editorWindow.pmDesignerParagraphPadding();
  var pLineHeight = editorWindow.pmDesignerParagraphLineHeight();
  var pFontFamily = editorWindow.pmDesignerParagraphFontFamily();

  // Grab the editor's markup as a string and clean it
  var docMarkup = editorWindow.document.documentElement.outerHTML;
  var docMarkupClean = getCleanedMarkupString(docMarkup, pPadding, pLineHeight, pFontFamily);

  // Reload the editors
  editorWindow.pmDesignerEnable();

  return docMarkupClean;
}


// Cleans a string suitable for use as a filename
function cleanFilename(filename) {
  return $.trim(filename).replace(/[^a-z0-9-_]/gi, '-').replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 100);
}


// Saves a snapshot to s3.  NOTE: FormData not compatible with IE<10
function saveSnapshot(saveSnapshotURL) {
  var filename = cleanFilename($('#save-email-name').val()),
      liveHTMLFormData = new FormData(),
      snapshotFormData = new FormData(),
      liveHTML = getLiveHTMLMarkup(),
      snapshot = getSnapshotMarkup(),
      liveHTMLBlob = new Blob([liveHTML], {type: 'text/html'}),
      snapshotBlob = new Blob([snapshot], {type: 'text/html'});

  liveHTMLFormData.append('file', liveHTMLBlob, filename + '.html');
  liveHTMLFormData.append('extension_groupname', 'html');
  liveHTMLFormData.append('protocol', 'http://');
  snapshotFormData.append('file', snapshotBlob, filename + '.snapshot.html');
  snapshotFormData.append('extension_groupname', 'html');
  snapshotFormData.append('protocol', 'http://');

  // Could probably combine these ajax calls into a single request,
  // but it'd require a new view to handle multiple files
  $.when(
    $.ajax({
      cache: false,
      contentType: false,
      data: liveHTMLFormData,
      dataType: 'json',
      method: 'POST',
      processData: false,
      url: saveSnapshotURL
    }),
    $.ajax({
      cache: false,
      contentType: false,
      data: snapshotFormData,
      dataType: 'json',
      method: 'POST',
      processData: false,
      url: saveSnapshotURL
    })
  )
    .done(function(liveArgs, snapshotArgs) {
      var liveLink = liveArgs[0].link,
          snapshotLink = snapshotArgs[0].link;
      $('#saved-live-url').text(liveLink);
      $('#saved-snapshot-url').text(snapshotLink);
      $('#save-changes-modal')
        .find('.save-changes-inprogress')
          .addClass('hidden')
          .end()
        .find('.save-changes-success')
          .removeClass('hidden');
    })
    .fail(function() {
      $('#save-changes-modal')
        .find('.save-changes-inprogress')
          .addClass('hidden')
          .end()
        .find('.save-changes-failure')
          .removeClass('hidden');
    });
}


function init(getSnapshotsURL, saveSnapshotURL, validKeyPath) {
  var $templateSelect = $('#template-select'),
      $snapshotListItemMarkup = $('#load-snapshot-list').find('.snapshot-wrapper').detach().first(),
      currentTemplate = '',
      currentTemplateVal = '';

  // Load the current template
  $(window).on('load', function() {
    // Catch a cached value from the browser
    currentTemplate = $templateSelect.find('option:selected').text();
    currentTemplateVal = $templateSelect.val();

    // Force default to be whatever the 2nd option is
    if (currentTemplateVal === '') {
      currentTemplate = $templateSelect.find('option:nth-child(2)').text();
      currentTemplateVal = $templateSelect.find('option:nth-child(2)').val();
      $templateSelect.val(currentTemplateVal);
    }

    loadTemplate(currentTemplateVal, true);
  });

  // Change the template when an option from the dropdown is selected.
  // Prompt the user if they're okay with losing any changes before
  // switching from a non-empty template.
  $templateSelect.on('change', function() {
    var newTemplateVal = $(this).val();

    if (window.confirm('Are you sure you want to switch templates? You will lose all changes made in the editor.')) {
      currentTemplateVal = newTemplateVal;
      currentTemplate = $(this).find('option:selected').text();
      loadTemplate(newTemplateVal, true);
    }
    else {
      $(this).val(currentTemplateVal);
    }
  });

  // Fetch and render a list of existing snapshots when Load Snapshot modal is
  // toggled
  $('#load-snapshot-modal').on('show.bs.modal', function() {
    getExistingSnapshots(getSnapshotsURL, $snapshotListItemMarkup);
  });

  // Load snapshot when Load Snapshot btn is clicked
  $('#load-snapshot').on('click', function() {
    loadSnapshot(validKeyPath);
  });

  $('#save-changes').on('click', function() {
    saveSnapshot(saveSnapshotURL);
  });
}
