ckan.module('scheming-repeating-subfields', function($) {
  return {
    initialize: function() {
      $.proxyAll(this, /_on/);

      var $template = this.el.children('div[name="repeating-template"]');
      this.template = $template.html();
      $template.remove();

      this.el.find('a[name="' + this.options.field_name + '-repeating-add"]').on("click", this._onCreateGroup);
      this.el.on('click', 'a[name="' + this.options.field_name + '-repeating-remove"]', this._onRemoveGroup);
    },

    /**
     * Add new group to the fieldset.
     *
     * Fields inside every new group must be renamed in order to form correct
     * structure during validation:
     *
     *  ...
     *  (parent, INDEX-1, child-1),
     *  (parent, INDEX-1, child-2),
     *  ---
     *  (parent, INDEX-2, child-1),
     *  (parent, INDEX-2, child-2),
     *  ...
     */
    _onCreateGroup: function(e) {
        var $last = this.el.find('.scheming-subfield-group').last();
        var group = ($last.data('groupIndex') + 1) || 0;
        var $copy = $(
  	    this.template.replace(new RegExp(this.options.field_name + '-REPEATING-INDEX0', 'g'), group)
          .replace(new RegExp(this.options.field_name + '-REPEATING-INDEX1', 'g'), group + 1));
        this.el.find('[name="' + this.options.field_name + '-subfields-group"]').append($copy);

      	this.initializeModules($copy);
        $copy.hide().show(100);
        $copy.find('input').first().focus();
        // hook for late init when required for rendering polyfills
        this.el.trigger('scheming.subfield-group-init');
        e.preventDefault();
    },

    /**
     * Remove existing group from the fieldset.
     */
    _onRemoveGroup: function(e) {
        var $curr = $(e.target).closest('.scheming-subfield-group');
        var $body = $curr.find('.panel-body.fields-content[data-field-name="' + this.options.field_name + '"]');
        var $button = $curr.find('a[name="' + this.options.field_name + '-repeating-remove"]');
        var $removed = $curr.find('.panel-body.fields-removed-notice[data-field-name="' + this.options.field_name + '"]');
        $button.hide();
        $removed.show(100);
        $body.hide(100, function() {
          $body.html('');
        });
        e.preventDefault();
    },

    /**
     * Enable functionality of data-module attribute inside dynamically added
     * groups.
     */
    initializeModules: function(tpl) {
      $('[data-module]', tpl).each(function (index, element) {
        ckan.module.initializeElement(this);
      });
    }
  };
});
