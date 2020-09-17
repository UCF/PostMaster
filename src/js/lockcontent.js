$('#lockContentModal').on('show.bs.modal', function (event) {
  const button = $(event.relatedTarget);
  const isLock = Boolean(button.data('lock'));
  const content = button.data('content');
  const formUrl = button.data('form-url');
  const modal = $(this);
  modal.find('.modal-title').text(content);
  modal.find('.modal-content form').attr('action', formUrl);
  modal.find('.modal-body .lock-content').text(content);
  // Assume the html already has the checkbox checked by default
  if (!isLock) {
    modal.find('#id_lock_content').removeAttr('checked');
  }
});
