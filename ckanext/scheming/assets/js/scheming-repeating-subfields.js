this.ckan.module('scheming-repeating-subfields', function($, _) {
  return {
    initialize: function() {
      var container = this;
      var $this = $(this.el);
      var $template = $this.children('div[name="repeating-template"]');
      var template = $template.html();
      var $add = $this.find('a[name="repeating-add"]');
      $template.remove();

      $add.on('click', function(e) {
        var $last = $this.find('.scheming-subfield-group').last();
        var group = ($last.data('groupIndex') + 1) || 0;
        var $copy = $(
          template.replace(/REPEATING-INDEX0/g, group)
          .replace(/REPEATING-INDEX1/g, group + 1));
        $this.find('.scheming-repeating-subfields-group').append($copy);
        $copy.hide().show(100);
        $copy.find('input').first().focus();
        // hook for late init when required for rendering polyfills
        $this.trigger('scheming.subfield-group-init');
        e.preventDefault();
      });

      $(document).on('click', 'a[name="repeating-remove"]', function(e) {
        var $curr = $(this).closest('.scheming-subfield-group');
        var $body = $curr.find('.panel-body.fields-content');
        var $button = $curr.find('.btn-repeating-remove');
        var $removed = $curr.find('.panel-body.fields-removed-notice');
        $button.hide();
        $removed.show(100);
        $body.hide(100, function() {
          $body.html('');
        });
        e.preventDefault();
      });
    }
  };
});
