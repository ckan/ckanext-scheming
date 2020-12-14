this.ckan.module('scheming-repeating-subfields', function($, _) {
    return {
        initialize: function() {
            var container = this,
                $this = $(this.el),
                $template = $this.children('div[name="repeating-template"]'),
                template = $template.html(),
                $add = $this.find('a[name="repeating-add"]');
            $template.remove();

            $add.on('click', function(e) {
                var $last = $this.find('.scheming-subfield-group').last(),
                    group = $last.data('groupIndex') + 1,
                    $copy = $(
                        template.replace(/REPEATING-INDEX0/g, group)
                        .replace(/REPEATING-INDEX1/g, group + 1));
                $copy.insertAfter($last).hide().show(100);
                // hook for late init when required for rendering polyfills
                $this.trigger('scheming.subfield-group-init');
                e.preventDefault();
            });

            $(document).on('click', 'a[name="repeating-remove"]', function(e) {
                var $curr = $(this).closest('.scheming-subfield-group'),
                    $body = $curr.find('.panel-body.fields-content'),
                    $button = $curr.find('.remove-button'),
                    $removed = $curr.find('.panel-body.fields-removed-notice');
                $button.hide();
                $removed.show(100);
                $body.hide(100, function() {
                  if($body.html()) {
                    $body.data('undo_html', $body.html());
                    $body.html('')
                  }
                });
                e.preventDefault();
            });

            $(document).on('click', 'a[name="repeating-undo-remove"]', function(e) {
                var $curr = $(this).closest('.scheming-subfield-group'),
                    $removed = $curr.find('.panel-body.fields-removed-notice'),
                    $button = $curr.find('.remove-button'),
                    $body = $curr.find('.panel-body.fields-content');
                if($body.data('undo_html')) {
                  $removed.hide(100);
                  $button.show();
                  $body.html($body.data('undo_html')).show(100);
                  $curr.data('undo_html', undefined);
                  $this.trigger('scheming.subfield-group-init');
                }
                e.preventDefault();
            });
        }
    };
});
