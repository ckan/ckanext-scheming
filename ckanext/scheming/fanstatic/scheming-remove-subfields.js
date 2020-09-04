this.ckan.module('scheming-remove-subfields', function (jQuery, _) {
  return {
    /* An object of module options */
    options: {
      /* Locale options can be overidden with data-module-i18n attribute */
      i18n: {
        heading: _('Please Confirm Action'),
        content: _('Are you sure you want to perform this action?'),
        confirm: _('Confirm'),
        cancel: _('Cancel')
      },
      template: [
        '<div class="modal">',
        '<div class="modal-header">',
        '<h3></h3>',
        '</div>',
        '<div class="modal-body"></div>',
        '<div class="modal-footer">',
        '<button class="btn btn-cancel"></button>',
        '<button class="btn btn-primary"></button>',
        '</div>',
        '</div>'
      ].join('\n')
    },

    /* Sets up the event listeners for the object. Called internally by
     * module.createInstance().
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.el.on('click', this._onClick);
    },

    /* Presents the user with a confirm dialogue to ensure that they wish to
     * continue with the current action.
     *
     * Examples
     *
     *   jQuery('.delete').click(function () {
     *     module.confirm();
     *   });
     *
     * Returns nothing.
     */
    confirm: function () {
      this.sandbox.body.append(this.createModal());
      this.modal.show();
    },

    /* Performs the action for the current item.
     *
     * Returns nothing.
     */
    performAction: function () {
      var $groups = this.sandbox.body.find('.scheming-subfield-group'),
          $curr = this.el.closest('.scheming-subfield-group'),
          count = $groups.length,
          $add = this.sandbox.body.find('a[name="repeating-add"]');
      if(count == 1){
        $add.click();
        count +=1;
      }
      $curr.remove();
      this.modal.hide();
    },

    /* Creates the modal dialog, attaches event listeners and localised
     * strings.
     *
     * Returns the newly created element.
     */
    createModal: function () {
      if (!this.modal) {
        var element = this.modal = jQuery(this.options.template);
        element.on('click', '.btn-primary', this._onConfirmSuccess);
        element.on('click', '.btn-cancel', this._onConfirmCancel);
        //element.modal({show: false});
          element.hide();

        element.find('h3').text(this.i18n('heading'));
        element.find('.modal-body').text(this.i18n('content'));
        element.find('.btn-primary').text(this.i18n('confirm'));
        element.find('.btn-cancel').text(this.i18n('cancel'));
      }
      return this.modal;
    },

    /* Event handler that displays the confirm dialog */
    _onClick: function (event) {
      event.preventDefault();
      this.confirm();
    },

    /* Event handler for the success event */
    _onConfirmSuccess: function (event) {
      this.performAction();
    },

    /* Event handler for the cancel event */
    _onConfirmCancel: function (event) {
      this.modal.hide();
    }
  };
});
