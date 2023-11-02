var scheming_multiple_text_init_done = false;
this.ckan.module('scheming-multiple-text', function($, _) {
  MultipleText = {

     multiple_add: function(field_name){
      var fieldset = $('fieldset[name='+field_name+']');
      let list = fieldset.find('ol')
      let items = list.find('li')
      var copy = items.last().clone();
      let input = copy.find('input');
      input.val('');
      list.append(copy);
      input.focus();
    },
    initialize: function() {
      if (!scheming_multiple_text_init_done) {
        $(document).on('click', 'a[name="multiple-remove"]', function(e) {
          var list = $(this).closest('ol').find('li');
          if (list.length != 1){
              var $curr = $(this).closest('.multiple-text-field');
              $curr.hide(100, function() {
                  $curr.remove();
              });
              e.preventDefault();
          }
          else{
               list.first().find('input').val('');
          }
        });
        scheming_multiple_text_init_done = true;
      }
    }
  };
  return MultipleText;
});
