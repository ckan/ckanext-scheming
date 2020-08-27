this.ckan.module('scheming-repeating-subfields', function (jQuery, _) {
    return {
        initialize: function() {
            var container = this,
                $this = $(this.el),
                $template = $this.children('div[name="repeating-template"]'),
                template = $template.html(),
                $add = $this.children('a[name="repeating-add"]');
            $template.remove();

            $add.on('click', function(e) {
                var $last = $this.find('.scheming-subfield-group').last(),
                    group = $last.data('groupIndex') + 1,
                    $copy = $(
                        template.replace(/REPEATING-INDEX0/g, group)
                        .replace(/REPEATING-INDEX1/g, group + 1));
                $copy.insertAfter($last);
                // hook for late init when required for rendering polyfills
                $this.trigger('scheming.subfield-group-init');
                e.preventDefault();
            });
        }
    };
});
