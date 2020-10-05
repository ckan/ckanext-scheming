this.ckan.module('scheming-repeating-subfields', function (jQuery, _) {
    return {
        options: {
          /* Locale options can be overidden with data-module-i18n attribute */
          i18n: {
            content: _('These fields have been removed, click save below to update the record with your changes.')
          }
        },
        initialize: function() {
            var container = this,
                $this = $(this.el),
                $template = $this.children('div[name="repeating-template"]'),
                template = $template.html(),
                $add = $this.children('a[name="repeating-add"]'),
                $remove = $this.find('a[name="repeating-remove"]'),
                $count = $this.find('.scheming-subfield-group').length-1;
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
                $count+=1;
                e.preventDefault();
            });

            $remove.on('click', function(e) {
                var $groups = $this.find('.scheming-subfield-group'),
                    $curr = $(this).closest('.scheming-subfield-group'),
                    $body = $curr.find('.panel-body'),
                    index = $curr.data('groupIndex'),
                    field = $curr.data('field');
                $count -=1;
                if($count == 0){
                    $add.click();
                  }
                $body.html(container.i18n('content'));
            });
        }
    };
});
