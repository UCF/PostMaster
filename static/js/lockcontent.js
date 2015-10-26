$('#lockContentModal').on('show.bs.modal', function (event) {
  var button = $(event.relatedTarget);
  var isLock = Boolean(button.data('lock'));
  var content = button.data('content');
  var formUrl = button.data('form-url');
  var modal = $(this);
  modal.find('.modal-title').text(content);
  modal.find('.modal-content form').attr('action', formUrl);
  modal.find('.modal-body .lock-content').text(content);
  // Assume the html already has the checkbox checked by default
  if (!isLock) {
    modal.find('#id_lock_content').removeAttr('checked');
  }
});
