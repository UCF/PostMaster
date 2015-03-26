(function() {
  'use strict';

  var recipientCreatePage = false,
      $attributeContainer = $('.attribute-container'),
      $addAttrContainer = $('.add-attr-container'),
      $clonedAttribute;

  function reorderAttributes() {
    $attributeContainer.find('.attribute').each(function( index ) {
      $(this).find('input').eq(0).attr('id','id_attributes-' + index + '-name').attr('name','id_attributes-' + index + '-value');
      $(this).find('input').eq(1).attr('id','id_attributes-' + index + '-name').attr('name','id_attributes-' + index + '-value');
      $(this).find('input').eq(2).attr('id','id_attributes-' + index + '-name').attr('name','id_attributes-' + index + '-value');
    });
  }

  function updateTotalForms() {
    $('#id_attributes-TOTAL_FORMS').val($attributeContainer.find('.attribute').length);
  }

  function incrementNumberInString(string) {
    return string.replace(/\d+/g, function(n){ return ++n; });
  }

  function addAttribute(e) {
    e.preventDefault();
    var $newAttribute = $clonedAttribute.clone().removeClass('hide');
    // For recipitent update increment the input field index
    if(!recipientCreatePage) {
      $newAttribute.find('input').each(function() {
        $(this).attr('id', incrementNumberInString($(this).attr('id')));
        $(this).attr('name', incrementNumberInString($(this).attr('name')));
      });
    }
    $newAttribute.appendTo($attributeContainer).fadeIn();
    // For recipient create
    if(recipientCreatePage) {
      reorderAttributes();
    }
    updateTotalForms();
  }

  function deleteAttribute(e) {
    e.preventDefault();
    if(recipientCreatePage) {
      reorderAttributes();
    } else {
      $(e.target).next().prop( "checked", true );
    }
    $(e.target).closest('.attribute').fadeOut();
    updateTotalForms();
  }

  function highlightRowToggle(e) {
    $(e.target).closest('.form-group').toggleClass('alert-' + $(e.target).attr('data-color'));
  }

  function init() {
    recipientCreatePage = (window.location.pathname.toString().indexOf('recipient/create/') !== -1);
    $clonedAttribute = $attributeContainer.find('.attribute').last().clone().appendTo('body').addClass('hide');
    // Select the first form input
    $('form:first *:input[type!=hidden]:input[type!=checkbox]:first').focus();
    // Add attribute button
    $('.add-attr-btn').on('click', addAttribute);
    // Delete attribute button
    $attributeContainer.on('click', 'span', deleteAttribute);
    // mouse over event
    $attributeContainer.on('mouseover', 'span', highlightRowToggle);
    $addAttrContainer.on('mouseover', 'span', highlightRowToggle);
    // mouse out event
    $attributeContainer.on('mouseout', 'span', highlightRowToggle);
    $addAttrContainer.on('mouseout', 'span', highlightRowToggle);
  }

  $(init);

}());
