// Loads a template via ajax (stored in static media dir).
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
  }).done(function(data) {
    template = data;
    loadEditor(template);
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
    // Disable markup generator if editor window is empty
    $('#generate-markup').attr('disabled', 'disabled');
  }
  else {
    $('#generate-markup').removeAttr('disabled');
  }
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
  // Replace all .pm-template-editable-paragraph p tags with tables
  // (<p> tags are too inconsistent across email clients.)
  $domDoc
    .find('.pm-template-editable-paragraph p span')
      .css('line-height', 'inherit')
      .end()
    .find('.pm-template-editable-paragraph p')
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
  var docType = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">';
  var docMarkupClean = docType + domDoc.documentElement.outerHTML;

  return docMarkupClean;
}


// Generate markup from iframe contents and paste it into #generated-markup
function generateMarkup() {
  var $markupContainer = $('#generated-markup');
  var editorWindow = document.getElementById('editor-window').contentWindow;

  // Stop here if the editor window doesn't exist (should never reach this
  // point, but just in case)
  if (!editorWindow) {
    return;
  }

  // Empty the markup container
  $markupContainer.text('');

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

  // Add the cleaned markup to $markupContainer
  $markupContainer.text(docMarkupClean);

  // Reload the editors
  editorWindow.pmDesignerEnable();
}


// Retrieve existing snapshots
function getExistingSnapshots(getSnapshotsURL, $snapshotList, $snapshotListItemMarkup) {
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
  }).done(function(data) {
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
  });
}


// Loads a snapshot from the snapshot select modal form
function loadSnapshot($snapshotList, $snapshotByURL) {
  snapshotURL = '';
  snapshotListVal = $snapshotList.find('input[type="radio"]:checked').val();
  snapshotByURLVal = $snapshotByURL.val();

  if (snapshotListVal) {
    snapshotURL = snapshotListVal;
  }
  else if (snapshotByURLVal) {
    snapshotURL = snapshotByURLVal;
  }

  // Ensure returned url is protocol relative
  snapshotURL = snapshotURL.replace(/^https?:\/\//, '//');

  loadTemplate(snapshotURL);
}


// Saves a snapshot to s3.  NOTE: not compatible with IE<10
// (TODO: set filename and contents from editor)
function saveSnapshot(saveSnapshotURL) {
  var liveHTMLFormData = new FormData(),
      snapshotFormData = new FormData(),
      liveHTMLBlob = new Blob(['cleaned contents from editor window will go here'], {type: 'text/html'}),
      snapshotBlob = new Blob(['snapshot from editor window will go here'], {type: 'text/html'});
  // TODO can this be cleaned up?
  liveHTMLFormData.append('file', liveHTMLBlob, 'myfilename.html');
  liveHTMLFormData.append('extension_groupname', 'html');
  liveHTMLFormData.append('protocol', 'http://');
  snapshotFormData.append('file', snapshotBlob, 'myfilename.snapshot.html');
  snapshotFormData.append('extension_groupname', 'html');
  snapshotFormData.append('protocol', 'http://');

  // Could probably combine these ajax calls into a single request,
  // but it'd require a new view to handle multiple files
  $.ajax({
    cache: false,
    contentType: false,
    data: liveHTMLFormData,
    dataType: 'json',
    method: 'POST',
    processData: false,
    url: saveSnapshotURL
  }).done(function(data) {
    $('#saved-live-url').text(data.link);
  });

  $.ajax({
    cache: false,
    contentType: false,
    data: snapshotFormData,
    dataType: 'json',
    method: 'POST',
    processData: false,
    url: saveSnapshotURL
  }).done(function(data) {
    $('#saved-snapshot-url').text(data.link);
  });
}


function init(getSnapshotsURL, saveSnapshotURL) {
  // TODO: clean up
  var $templateSelect = $('#template-select'),
      $snapshotModal = $('#load-snapshot-modal'),
      $snapshotList = $snapshotModal.find('#load-snapshot-list'),
      $snapshotByURL = $snapshotModal.find('#load-snapshot-urlfield'),
      $snapshotListItemMarkup = $snapshotList.find('.snapshot-wrapper').detach().first(),
      currentTemplate = '',
      currentTemplateVal = '';

  // Load the current template (if the browser has cached a selection)
  $(window).on('load', function() {
    currentTemplate = $templateSelect.find('option:selected').text();
    currentTemplateVal = $templateSelect.val();
    loadTemplate(currentTemplateVal, true);
  });

  // Change the template when an option from the dropdown is selected.
  // Prompt the user if they're okay with losing any changes before
  // switching from a non-empty template.
  $templateSelect.on('change', function() {
    var newTemplateVal = $(this).val();

    if (currentTemplateVal !== '') {
      if (window.confirm('Are you sure you want to switch templates? You will lose all changes made in the editor.')) {
        currentTemplateVal = newTemplateVal;
        currentTemplate = $(this).find('option:selected').text();
        loadTemplate(newTemplateVal, true);
      }
      else {
        $(this).val(currentTemplateVal);
      }
    }
    else {
      currentTemplateVal = newTemplateVal;
      currentTemplate = $(this).find('option:selected').text();
      loadTemplate(newTemplateVal, true);
    }
  });

  // Generate email markup from editor when Generate Markup btn is clicked
  $('#generate-markup').on('click', generateMarkup);

  // Fetch and render a list of existing snapshots when Load Snapshot modal is
  // toggled
  $('#load-snapshot-modal').on('show.bs.modal', function() {
    getExistingSnapshots(getSnapshotsURL, $snapshotList, $snapshotListItemMarkup);
  });

  // Load snapshot when Load Snapshot btn is clicked
  $('#load-snapshot').on('click', function() {
    loadSnapshot($snapshotList, $snapshotByURL);
  });

  $('#save-changes').on('click', function() {
    saveSnapshot(saveSnapshotURL);
  });
}
