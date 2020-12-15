this.ckan.module('scheming-multiple-text', function($, _) {
  return {
    initialize: function() {
      var container = this;
      var $this = $(this.el);
      var $template = $this.children('div[name="multiple-template"]');
      var template = $template.html();
      var $add = $this.find('a[name="multiple-add"]');
      $template.remove();

      $add.on('click', function(e) {
        var $copy = $(template);
        $this.find('.multiple-text-group').append($copy);
        $copy.hide().show(100);
        e.preventDefault();
      });

      $(document).on('click', 'a[name="multiple-remove"]', function(e) {
        var $curr = $(this).closest('.multiple-text-field');
        $curr.hide(100, function() {
          $curr.remove();
        });
        e.preventDefault();
      });
    }
  };
});
