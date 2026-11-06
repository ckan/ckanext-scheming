this.ckan.module('scheming-multiple-text', function ($, _) {
  return {
    initialize: function () {
      $.proxyAll(this, /_on/);
      this.el.on('click', 'a[name="multiple-remove"]', this._onRemove);
      this.el.on('click', 'a[name="multiple-add"]', this._onAdd);
    },

    _onAdd: function (e) {
      e.preventDefault();
      var list = this.el.find('ol');
      var copy = list.find('li').last().clone();
      var input = copy.find('input').val('');
      list.append(copy);
      input.focus();
    },

    _onRemove: function (e) {
      e.preventDefault();
      var list = this.el.find('ol').find('li');
      if (list.length != 1) {
        var $curr = $(e.currentTarget).closest('.multiple-text-field');
        $curr.hide(100, function () {
          $curr.remove();
        });
      } else {
        list.first().find('input').val('');
      }
    }
  };
});
