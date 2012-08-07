$().ready(function() {

	$('tr')
		.each(function(index, row) {
			var row      = $(row),
				link_url = row.attr('data-link-url');
			if(typeof link_url != 'undefined') {
				row.hover(
					function() {$(this).css('cursor', 'pointer');},
					function() {$(this).css('cursor', 'none');}
				);
				row.click(function() {window.location = link_url});
			}
		})
});