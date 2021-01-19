var scheming_multiple_text_init_done = false;
this.ckan.module('scheming-multiple-text', function($, _) {
  return {
    initialize: function() {
      var container = this;
      var $this = $(this.el);
      var $template = $this.children('div[name="multiple-template"]');
      var template = $template.html();
      $template.remove();

      if (!scheming_multiple_text_init_done) {
        $(document).on('click', 'a[name="multiple-add"]', function(e) {
          var $copy = $(template);
          $(this).closest('.scheming-fieldset').find('.multiple-text-group').append($copy);
          $copy.hide().show(100);
          $copy.find('input').focus();
          e.preventDefault();
        });

        $(document).on('click', 'a[name="multiple-remove"]', function(e) {
          var $curr = $(this).closest('.multiple-text-field');
          $curr.hide(100, function() {
            $curr.remove();
          });
          e.preventDefault();
        });
        scheming_multiple_text_init_done = true;
      }
    }
  };
});
