this.ckan.module('scheming-repeating-subfields', function (jQuery, _) {
    return {
        initialize: function() {
            var container = this,
                $this = $(this.el),
                $template = $this.children('div[name="repeating-template"]'),
                template = $template.html(),
                $add = $this.children('a[name="repeating-add"]'),
                $remove = $this.find('a[name="repeating-remove"]');
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

            $remove.on('click', function(e) {
                var $groups = $this.find('.scheming-subfield-group'),
                    $curr = $(this).closest('.scheming-subfield-group'),
                    index = $curr.data('groupIndex'),
                    count = $groups.length;
                document.getElementById("statusText1").innerHTML = (index+1)+"?";
                document.getElementById("statusText0").style.display = 'inline';
                document.getElementById("statusText1").style.display = 'inline';
                document.getElementById("statusText2").style.display = 'none';
                //if(count !== 1){
                    $("#confirmRemoval").on('click', function(e) {
                        if(count ==1){
                            $add.click();
                            count +=1;
                        }
                        $curr.remove();
                    });
                // }else{
                //     $add.click();
                //     $curr.remove();
                // }

                e.preventDefault();
            });
        }
    };
});
