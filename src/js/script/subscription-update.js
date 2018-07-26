var subscriptionUpdate = function($) {
    if ($('#unsubscribe-all').length === 0) return;

    $('#unsubscribe-all').on('click', function() {
        $('input[type="checkbox"][name="subscription_categories"]').prop('checked', false);
    });
};

if (typeof jQuery !== 'undefined') {
    jQuery(document).ready(function($) {
        subscriptionUpdate($);
    });
}
