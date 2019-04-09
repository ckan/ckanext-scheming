this.ckan.module('scheming-subfields', function (jQuery, _) {
    return {
        initialize: function() {
            var container = this,
                $add = $('<a href="#" class="btn btn-success"><i class="fa fa-plus" aria-hidden="true"></i></a>');
                $remove = $('<a href="#" class="btn btn-danger"><i class="fa fa-minus" aria-hidden="true"></i></a>');

            $add.on('click', function(e) {
                container.add_group();
                e.preventDefault();
            });

            $remove.on('click', function(e) {
                container.remove_group();
                e.preventDefault();
            });

            $(this.el).append($add);
            $(this.el).append($remove);
        },

        add_group: function() {
            var $this = $(this.el),
                $last = $this.find('.scheming-subfield-group').last(),
                $copy = $last.clone();


            var group = parseInt($copy.data('groupIndex'), 10) + 1,
                field = $copy.data('field');

            $copy.attr('data-group-index', group);

            function replace_index(index, string) {
                return string.replace(new RegExp('(^' + field + '-)([0-9]+)'), '$1' + group);
            };

            /* Find and increment the field name IDs */
            $copy.find('*[name^="' + field + '-"]')
                .attr('name', replace_index)
                .attr('id', replace_index);

            $copy.find(':input').val('');

            $copy.insertAfter($last);
        },

        remove_group: function() {
            var $this = $(this.el),
                $groups = $this.find('.scheming-subfield-group'),
                $last = $groups.last(),
                count = $groups.length;

            if(count !== 1) {
                $last.remove();
            }
        }
    };
});
