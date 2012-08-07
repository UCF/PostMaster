$().ready(function() {

	$('tr[data-link-url!=""]')
		.each(function(index, row) {
			var row      = $(row),
				link_url = row.attr('data-link-url');
			row.click(function() {window.location = link_url});
		})
});