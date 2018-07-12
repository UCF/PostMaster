(function() {
  'use strict';

  var recipientCreatePage = false,
      $attributeContainer = $('.attribute-container'),
      $addAttrContainer = $('.add-attr-container'),
      $totalForms = $('#id_attributes-TOTAL_FORMS'),
      $clonedAttribute;

  function reorderAttributes() {
    $attributeContainer.find('.attribute').each(function( index ) {
      var $input = $(this).find('input');
      $input.eq(0).attr('id','id_attributes-' + index + '-id').attr('name','attributes-' + index + '-id');
      $input.eq(1).attr('id','id_attributes-' + index + '-name').attr('name','attributes-' + index + '-name');
      $input.eq(2).attr('id','id_attributes-' + index + '-value').attr('name','attributes-' + index + '-value');
    });
  }

  function updateTotalForms() {
    $totalForms.val($attributeContainer.find('.attribute').length);
  }

  function incrementNumberInString(string) {
    return string.replace(/\d+/g, function(n){ return ++n; });
  }

  function addAttribute(e) {
    e.preventDefault();
    var $newAttribute = $clonedAttribute.clone().removeClass('d-none');
    $newAttribute.appendTo($attributeContainer);
    // recipient create
    if(recipientCreatePage) {
      reorderAttributes();
    // recipient update
    } else {
      $newAttribute.find('input').each(function() {
        $(this).attr('id', incrementNumberInString($(this).attr('id')));
        $(this).attr('name', incrementNumberInString($(this).attr('name')));
      });
    }
    updateTotalForms();
  }

  function deleteAttribute(e) {
    e.preventDefault();
    // recipient create
    if(recipientCreatePage) {
      $(e.target).closest('.attribute').remove();
      reorderAttributes();
    // recipient update
    } else {
      $(e.target).closest('.attribute').hide();
      $(e.target).next().prop( "checked", true );
    }
    updateTotalForms();
  }

  function highlightRowToggle(e) {
    $(e.target).closest('.form-group').toggleClass('alert-' + $(e.target).attr('data-color'));
  }

  function init() {
    recipientCreatePage = (window.location.pathname.toString().indexOf('recipient/create/') !== -1);
    $clonedAttribute = $attributeContainer.find('.attribute').last().clone().appendTo('body').addClass('d-none');
    // Select the first form input
    $('form:first *:input[type=text]:first').focus();
    // Add attribute button click handler
    $('.add-attr-btn').on('click', addAttribute);
    // Delete attribute button click handler
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
