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


this.ckan.module('select-process', function (jQuery, _) {
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
            // console.log(url);
            return response.json(); // parses JSON response into native JavaScript objects
        },

        handleDataSparql: function (data = null) {
            stored_option = null
            try{
                stored_option = JSON.parse($("#" + this.options.field)[0].value).uri
            }
            finally{
                for (var i = 0; i < data.results.bindings.length; i++) {
                    if (data.results.bindings[i].subject.value == stored_option) {
                        $(this.el[0]).append($('<option>', {
                            id: data.results.bindings[i].subject.value,
                            value: data.results.bindings[i].subject.value,
                            text: data.results.bindings[i].label.value,
                            selected: 'selected'
                        }));
                    }
                    else {
                        $(this.el[0]).append($('<option>', {
                            id: data.results.bindings[i].subject.value,
                            value: data.results.bindings[i].subject.value,
                            text: data.results.bindings[i].label.value
                        }));
                    }
                };
            }
            // console.log(data.results);

        },

        _onReady: function () {
            var input = $("#" + this.options.field)[0];
            var btn = $("#" + this.options.field + "-btn")[0];

            $(this.el[0]).on("change", function () {
                selected_as_json = {
                    "uri": $(this).children("option:selected").val(),
                    "label": $(this).children("option:selected").text()
                }
                $(input).val(JSON.stringify(selected_as_json))
            })




            if (this.options.mode = "sparql") {
                var fullUrl = this.options.source + "?query=" + encodeURIComponent(this.options.query);

                this.requestSparql(fullUrl)
                    .then(data => this.handleDataSparql(data))
                    .catch(error => {
                        console.error('There has been a problem while fetching data from triple store:', error);
                    });

            }


            $(btn).on('click', function (e) {
                e.preventDefault();
                window.open(window.location.origin + "/add-process")
            });

        }
    }
});