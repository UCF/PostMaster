(function() {
  'use strict';

  var recipientCreatePage = false,
      $attributeContainer = $('.attribute-container'),
      $clonedAttribute;

  function reorderAttributes() {
    $attributeContainer.find('.attribute').each(function( index ) {
      $(this).find('input').eq(0).attr('id','id_attributes-' + index + '-name').attr('name','id_attributes-' + index + '-value');
      $(this).find('input').eq(1).attr('id','id_attributes-' + index + '-name').attr('name','id_attributes-' + index + '-value');
    });
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
  }

  function deleteAttribute(e) {
    e.preventDefault();
    if(recipientCreatePage) {
      $(e.target).closest('.attribute').remove();
      reorderAttributes();
    } else {
      $(e.target)
        .next().prop( "checked", true )
        .closest('.attribute').fadeOut();
    }
  }

  function highlightRowMouseOver(e) {
    $(e.target).closest('.form-group').parent().find('.row').addClass('alert-' + $(e.target).attr('data-color'));
  }

  function highlightRowMouseOut(e) {
    $(e.target).closest('.form-group').parent().find('.row').removeClass('alert-' + $(e.target).attr('data-color'));
  }

  function init() {
    recipientCreatePage = (window.location.pathname.toString().indexOf('recipient/create/') !== -1);
    $clonedAttribute = $attributeContainer.find('.attribute').last().clone().appendTo('body').addClass('hide');
    // Select the first form input
    $('form:first *:input[type!=hidden]:input[type!=checkbox]:first').focus();
    // Add attribute button
    $('.add-attr-btn').on('click', addAttribute);
    // Delete attribute button
    $attributeContainer.on('click', '.delete-attr-btn', deleteAttribute);
    // mouse over event
    $attributeContainer.on('mouseover', '.delete-attr-btn, .add-attr-btn', highlightRowMouseOver);
    // mouse out event
    $attributeContainer.on('mouseout', '.delete-attr-btn, .add-attr-btn', highlightRowMouseOut);
  }

  $(init);

}());
