this.ckan.module('scheming-repeating-subfields', function (jQuery, _) {
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
                var $groups = $this.find('.scheming-subfield-group'),
                    $curr = $(this).closest('.scheming-subfield-group'),
                    $body = $curr.find('.panel-body');
                $body.hide(100, function() {
                  $body.html(container.i18n('removal-text')).show(200);
                });
            });
        }
    };
});
