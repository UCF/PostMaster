// Enables all editing functionality.
function pmDesignerEnable() {
  $('.pm-template-editable-single').editable({
    allowedTags: ['a', 'b', 'em', 'i', 's', 'strong', 'span', 'u'],
    buttons: ['bold', 'italic', 'underline', 'createLink', 'html'],
    imageMove: false,
    inlineMode: true,
    paragraphy: false,
    plainPaste: true,
    useClasses: false
  });

  $('.pm-template-editable-paragraph').editable({
    allowedTags: ['a', 'b', 'blockquote', 'br', 'col', 'colgroup', 'dd', 'div', 'dl', 'dt', 'em', 'hr', 'i', 'img', 'li', 'ol', 'p', 's', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul'],
    alwaysVisible: true,
    buttons: ['bold', 'italic', 'underline', 'fontSize', 'createLink', 'align', 'insertImage', 'html', 'customUnderline'],
    defaultImageAlignment: 'left',
    defaultImageWidth: 0,
    imageButtons: ['linkImage', 'replaceImage', 'removeImage'],
    imageMove: false,
    imageUpload: false,
    inlineMode: true,
    paragraphy: true,
    plainPaste: true,
    useClasses: false
  })
    .on('editable.imageInserted', function(e, editor, img) {
        img.addClass('responsiveimg');
    });

  $('.pm-template-editable-multiline').editable({
    allowedTags: ['a', 'b', 'blockquote', 'br', 'col', 'colgroup', 'dd', 'div', 'dl', 'dt', 'em', 'hr', 'i', 'img', 'li', 'ol', 's', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul'],
    alwaysVisible: true,
    buttons: ['bold', 'italic', 'underline', 'createLink', 'align', 'insertImage', 'html'],
    defaultImageAlignment: 'left',
    defaultImageWidth: 0,
    inlineMode: true,
    imageButtons: ['linkImage', 'replaceImage', 'removeImage'],
    imageMove: false,
    imageUpload: false,
    paragraphy: false,
    plainPaste: true,
    useClasses: false
  }).on('editable.imageInserted', function(e, editor, img) {
    img.addClass('responsiveimg');
  });
}


// Destroys all editing functionality.
function pmDesignerDestroy() {
  $('.pm-template-editable-container').each(function() {
    var markup = $(this).editable('getHTML', false, false);
    $(this)
      .html(markup)
      .editable('destroy');
  });
}


// Fixes .froala-box responsiveness on .pm-template-editable-paragraph.
function pmDesignerResponsiveParagraphs() {
  $('.pm-template-editable-paragraph.froala-box').each(function() {
    var $elem = $(this);
    $elem.width('1px');
    var newWidth = $elem.parent().innerWidth();
    $elem.width(newWidth);
  });
}


// Returns padding css styling for paragraphs within
// .pm-template-editable-paragraph
function pmDesignerParagraphPadding() {
  var $p = $('.pm-template-editable-paragraph').first().find('p');

  // Shorthand 'padding' is not supported by jquery, so get each value
  // separately + combine
  var top = $p.css('padding-top') || '0';
  var right = $p.css('padding-right') || '0';
  var bottom = $p.css('padding-bottom') || '0';
  var left = $p.css('padding-left') || '0';

  return top + ' ' + right + ' ' + bottom + ' ' + left;
}


// Returns calculated unitless line-height value for paragraphs within
// .pm-template-editable-paragraph
function pmDesignerParagraphLineHeight() {
  var $p = $('.pm-template-editable-paragraph').first().find('p');
  var lineHeightUnitless = 1.35; // default

  // jquery's .css() will (almost always) return values in
  // px format, despite what the actual set value is.  Assume we will
  // always get either unitless values (incorrectly, from an old
  // browser) or px values.
  var lineHeight = $p.css('line-height');
  var fontSize = $p.css('font-size');

  if (parseInt(lineHeight, 10) !== 0 && !lineHeight.match(/[a-z]/i)) {
    // unitless value returned (probably ie9 not calculating a unitless value to px)
    lineHeightUnitless = lineHeight;
  }
  else {
    lineHeightUnit = lineHeight.substring(lineHeight.length - 2, lineHeight.length);
    fontSizeUnit = fontSize.substring(fontSize.length - 2, fontSize.length);

    if (lineHeightUnit == 'px' && fontSizeUnit == 'px' && lineHeight !== '0px' && fontSize !== '0px') {
      lineHeightUnitless = parseInt(lineHeight, 10) / parseInt(fontSize, 10);
    }
    // give up and use fallback otherwise; we don't want to divide by 0
  }

  // Always return value rounded to 2 decimal places
  return lineHeightUnitless.toFixed(2);
}


// Returns font family for paragraphs within
// .pm-template-editable-paragraph
function pmDesignerParagraphFontFamily() {
  return $('.pm-template-editable-paragraph').first().find('p').css('font-family') || 'serif;';
}


function pmDesignerInit() {
  $.Editable.DEFAULTS.key = '{{ froala_license }}';
  $(window).on('load', pmDesignerEnable);
  $(window).on('load resize', pmDesignerResponsiveParagraphs);
}


pmDesignerInit();
