var Webcom   = {};

/*
 * Dynamically add items to formsets.
 * From: http://stackoverflow.com/questions/501719/dynamically-adding-a-form-to-a-django-formset-with-ajax
 *
 */
function extend_formset(selector, type) {
	var newElement = $(selector).clone(false);
	var total = $('#id_' + type + '-TOTAL_FORMS').val();
	newElement.find(':input').each(function() {
		var name = $(this).attr('name').replace('-' + (total-1) + '-','-' + total + '-');
		var id = 'id_' + name;
			$(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
	});
	newElement.find('label').each(function() {
		var newFor = $(this).attr('for').replace('-' + (total-1) + '-','-' + total + '-');
			$(this).attr('for', newFor);
	});
	total++;
	$('#id_' + type + '-TOTAL_FORMS').val(total);
	$(selector).after(newElement);
	return newElement;
}

$().ready(function(){
	
});