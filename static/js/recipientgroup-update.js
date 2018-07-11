(function() {
    $('#tb_recipient_search').focus();

    // TODO: fix type ahead

    // var recipients = new Bloodhound({
    //         datumTokenizer: Bloodhound.tokenizers.obj.whitespace('email_address'),
    //         queryTokenizer: Bloodhound.tokenizers.whitespace,
    //         remote: '/recipients/json/?search=%QUERY'
    //     });

    //     recipients.clearPrefetchCache();

    //     recipients.initialize();

    //     $('#tb_recipient_search').typeahead({
    //         hint: false,
    //         minLength: 3,
    //         limit: 10,
    //         highlight: true
    //     },{
    //         displayKey: 'email_address',
    //         source: recipients.ttAdapter()
    //     });

    //     $('#tb_recipient_search').bind('typeahead:selected', function(obj, datum, name) {
    //         $('#tb_recipient_search').val(datum.email_address);
    //     });
})();
