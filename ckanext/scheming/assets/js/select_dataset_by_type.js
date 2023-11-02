
this.ckan.module('select-dataset-by-type', function (jQuery, _) {

	return {
		options: {
		},

		initialize: function () {

			jQuery.proxyAll(this, /_on/);
			this.el.ready(this._onReady);

		},

		_onReady: function () {


			var sel = $("#" + this.options.field + "-select")[0];
			var input = $("#" + this.options.field + "-input")[0];
			var list = $("#" + this.options.field + "-list")[0];
			var fieldValue = $("#" + this.options.field)[0];
			var btn = $("#" + this.options.field + "-btn")[0];
			var btnExt = $("#" + this.options.field + "-btn-ext")[0];
			
			var buildFieldValueFromList = function () {
				var result = '';
				$(list).find("li").each(function(i, el){
					if ( i !== 0) {
						result += ','; 
					}
					result += $(this).data('value');
				});
				$(fieldValue).val(result);
			};
			
			var appendValue = function (value, text) {
				$(list).append('<li data-value="' + value + '">'+ text + '<a></a></li>').on('click', 'li a', function () {
							$(this).parent('li').remove();
							buildFieldValueFromList();
						});
			};
			
			$(list).on('click', 'li a', function () {
				$(this).parent('li').remove();
				buildFieldValueFromList();
			});

			$(btn).on('click', function (e) {
				e.preventDefault();
				
				if ($(sel).val() != "") {
					appendValue($(sel).val(), $(sel).find('option:selected').text());
					buildFieldValueFromList();
				}
			});
			$(btnExt).on('click', function (e) {
				e.preventDefault();

				if ($(input).val() != "") {					
					appendValue($(input).val(), $(input).val());
					buildFieldValueFromList();
				}
			});

		}
	}
});