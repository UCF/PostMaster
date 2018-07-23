var subscriptionUpdate = function($) {
    $('#unsubscribe-all').on('click', function() {
        $('input[type="checkbox"][name="subscription_categories"]').prop('checked', false);
    });
};

if (typeof jQuery !== 'undefined') {
    jQuery(document).ready(function($) {
        subscriptionUpdate($);
    });
}