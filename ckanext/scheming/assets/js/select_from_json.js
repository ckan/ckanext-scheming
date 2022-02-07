/* A module for creating 
 *
 * mode		- mandatory: 2 options
 *			- "json": 	Request external JSON data directly
 *			- "sparql":	Request a sparql endpoint with specified query to get response as JSON
 * source 	- mandatory
 *			- in json-mode: An url pointing to a JSON source.
 *			- in sparql-mode: An url pointing to a sparql endpoint
 * query 	- only for sparql mode
 *
 * Examples
 *	
 */


this.ckan.module('select-from-json', function (jQuery, _) {

	return {
		options: {
			mode: null,
			source: '',
			query: ''
		},

		initialize: function () {

			jQuery.proxyAll(this, /_on/);
			this.el.ready(this._onReady);

		},

		requestSparql: async function (url = '') {
			const response = await fetch(url, {
				method: 'POST',
				headers: {
					'Accept': 'application/sparql-results+json'
				}
			});
			return response.json(); // parses JSON response into native JavaScript objects
		},

		requestJson: async function (url = '') {
			const response = await fetch(url, {
				method: 'POST',
				headers: {
					'Accept': 'application/json'
				}
			});
			return response.json(); // parses JSON response into native JavaScript objects
		},

		handleDataSparql: function (data = null) {
			for (var i = 0; i < data.results.bindings.length; i++) {
				if (data.results.bindings[i].subject.value == this.options.selected) {
					$(this.el[0]).append($('<option>', {
						value: data.results.bindings[i].subject.value,
						text: data.results.bindings[i].label.value,
						selected: 'selected'
					}));
				}
				else {
					$(this.el[0]).append($('<option>', {
						value: data.results.bindings[i].subject.value,
						text: data.results.bindings[i].label.value
					}));
				}
			};
		},

		_onReady: function () {


			var sel = this.el[0];
			var options = this.options;
			var divMain = $("#" + this.options.field + "-div")[0];
			var input = $("#" + this.options.field)[0];
			var btn = $("#" + this.options.field + "-btn")[0];
			var metrics = new Object();

			if (this.options.mode = "sparql") {
				var fullUrl = this.options.source + "?query=" + encodeURIComponent(this.options.query);

				this.requestSparql(fullUrl)
					.then(data => this.handleDataSparql(data))
					.catch(error => {
						console.error('There has been a problem while fetching data from triple store:', error);
					});
			}
			else {
				// TODO:  handle json
			}

			var createBlock = function (label, url, value) {

				// Create blocks default elements
				var block = $("<div>", { "class": "metrics-block"});
				block.append("<label>" + label + '</label>');
				block.append('<a remove="' + url + '" class="btn btn-default btn-sm pull-right">Remove</a>');
				block.append('<p class="tiny-metrics-url">' + url + '</p>');

				var inputs = $('<div>', { "class": "input-group" });
				for (var subvalue in value) {
					inputs.append('<div class="input-group-row"><span class="input-group-addon">' + subvalue + '</span><input name="' + url + '" type="text" value="' + value[subvalue] + '" /></div>');
				}

				// Set event handler to all inputs in current block
				inputs.find("input").on("input", (e) => updateMetric());
				
				// Set event handler to remove button in current block
				block.find("a").on("click", (e) => {
					e.target.closest('div.metrics-block').remove();
					updateMetric();	
				});

				block.append(inputs);
				$(divMain).append(block);
				
			};

			var updateMetric = function(){
				metrics = new Object();
				divMain.querySelectorAll("div[class='metrics-block']").forEach((node,index) => 
				{
					var metricUrl = $(node.querySelector("p[class='tiny-metrics-url'")).text()
					if(typeof metrics[metricUrl] === 'undefined') {
						metrics[metricUrl] = getEmptySubMetric($(node.querySelector("label")).text());	
					}
					else {
						metrics[metricUrl].values.push(getEmptyValuesObj());
					}
					
					node.querySelectorAll("span[class='input-group-addon'").forEach((subnode,subindex) => {
						metrics[metricUrl].values[metrics[metricUrl].values.length-1][$(subnode).text()] = $(subnode.nextElementSibling).val();
					});
				});
				$(input).val(JSON.stringify(metrics));
			};
			
			var getEmptySubMetric = function (label) {
				var result = {};
				
				result['label'] = label;
				result['values'] = new Array();
				result['values'].push(getEmptyValuesObj());

				return result;
			};
			
			var getEmptyValuesObj = function () {
				var subLabels = options.sublabels.split("|");
				var subValues = {};

				for (var i = 0; i < subLabels.length; i++) {
					subValues[subLabels[i]] = "";
				}
				return subValues;
			};

			if (this.el.data('metrics_data')) {
				metrics = this.el.data('metrics_data');
				for( var metric in metrics ) {
					// Backwards compatibility for previous datasets where values not saved as array
					if(Array.isArray(metrics[metric].values)) {
						for( var value in metrics[metric].values){
							createBlock(metrics[metric].label, metric, metrics[metric].values[value]);
						}
					}
					else {
						createBlock(metrics[metric].label, metric, metrics[metric].values);
					}
				}
			}

			$(btn).on('click', function (e) {
				e.preventDefault();

				if ($(sel).val() != "") {
					createBlock(sel.options[sel.selectedIndex].text, $(sel).val(), getEmptyValuesObj());
					updateMetric();
				}
			});

		}
	}
});