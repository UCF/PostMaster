$().ready(function() {

	/**
	 * If a <table> <tr> has a data-link-url attribute, make a click of that row
	 * link to the data-link-url value. Also, while hoving over that row, add the
	 * active class.
	 **/
	$('tr')
		.each(function(index, row) {
			var row      = $(row),
				link_url = row.attr('data-link-url');
			if(typeof link_url != 'undefined') {
				row.hover(
					function() {$(this).addClass('active');},
					function() {$(this).removeClass('active');}
				);
				row.click(function() {window.location = link_url});
			}
		})
});