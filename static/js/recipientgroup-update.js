(function () {
  $('#tb_recipient_search').focus();

  function getQuery() {
    return $('#tb_recipient_search').val();
  }

  var recipients = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('email_address'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
      wildcard: '%QUERY',
      url: '/recipients/json/?search=%QUERY'
    }
  });

  recipients.clearPrefetchCache();

  recipients.initialize();

  $('#tb_recipient_search').typeahead({
    hint: false,
    minLength: 3,
    limit: 10,
    highlight: true
  }, {
      displayKey: 'email_address',
      source: recipients.ttAdapter()
    });

  $('#tb_recipient_search').on('typeahead:selected', function (obj, datum, name) {
    $('#tb_recipient_search').val(datum.email_address);
  });
})();
