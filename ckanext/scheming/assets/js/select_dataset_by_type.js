
this.ckan.module('select-dataset-by-type', function (jQuery, _) {

	return {
		options: {
			mode: null
		},

		initialize: function () {

			jQuery.proxyAll(this, /_on/);
			this.el.ready(this._onReady);

		},
		
		

		_onReady: function () {


			var div = this.el[0];
			var sel = $("#" + this.options.field + "-select")[0];
			var input = $("#" + this.options.field + "-input")[0];
			var list = $("#" + this.options.field + "-list")[0];
			var fieldValue = $("#" + this.options.field)[0];
			var btn = $("#" + this.options.field + "-btn")[0];
			var btnExt = $("#" + this.options.field + "-btn-ext")[0];
			

			var getNextId = function () {
				var idList = [];
				idList.push(-1);
				$(list).find("li").each(function(){
					idList.push(Number($(this).data('id')));
				});
				return Math.max.apply(null,idList) + 1;
			};
			
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
			
			var appendValue = function (value) {
				$(list).append('<li data-id="' + getNextId() + '" data-value="' + value + '">'+ value + '<a></a></li>').on('click', 'li a', function () {
							$(this).parent('li').remove();
							buildFieldValueFromList();
						});
			};
			
			
			if ($(fieldValue).val().trim() != "") {
				var existingValues = $(fieldValue).val().split(',');
				existingValues.forEach(function(item){
					appendValue(item);
				});
			}

			$(btn).on('click', function (e) {
				e.preventDefault();
				
				if ($(sel).val() != "") {
					appendValue($(sel).val());
					buildFieldValueFromList();
				}
			});
			$(btnExt).on('click', function (e) {
				e.preventDefault();

				if ($(input).val() != "") {					
					appendValue($(input).val());
					buildFieldValueFromList();
				}
			});

		}
	}
});