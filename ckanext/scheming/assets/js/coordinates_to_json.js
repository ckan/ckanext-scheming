"use strict";

ckan.module('geokurmeta_coordinates_to_json', function ($) {
  return {
    initialize: function () {
		
		var myElement = $(this.el);
		var myParent = $(myElement.parent());
		var formSnippet = $(myParent.find('#coordForm'))[0];
		
		var myButton = $(myParent.find('button'));
		myButton.prop('popShown', false);
		myButton.text('enter coordinates');
		
		myButton.popover({html: true,
						sanitize: false,
						trigger: 'manual',
						title : 'Bounding Box in WGS84<a href="#" class="close" data-dismiss="alert">&times;</a>',
						content: $(formSnippet).html(),
						placement: 'top'});
		
		myParent.on("click", ".close" , function(){
			myButton.prop('popShown', false).popover('hide');
			myElement.prop('disabled', false);
			myButton.text('enter coordinates');
			myButton.removeClass('btn-success').addClass('btn-default');
		});
		
		function generateGeoJson(pointA, pointB) {	
			var pointC = pointB.split(',')[0] + ',' + pointA.split(',')[1];
			var pointD = pointA.split(',')[0] + ',' + pointB.split(',')[1];
			return '{ "type": "Polygon", "coordinates": [[\n  [' + pointA + '],\n  [' + pointC + '],\n  [' + pointB + '],\n  [' + pointD + '],\n  [' + pointA + ']\n ]]\n}'; 
		}
		
		function validCoordinatesGiven(pointA, pointB) { 
			if (!isNaN(pointA.split(',')[0]) &&  !isNaN(pointA.split(',')[1])) {
				$(myParent.find('.popover-content span')[0]).css( "color", "#555555" );
			}
			else {
				$(myParent.find('.popover-content span')[0]).css( "color", "red" );
				return false;
			}
			
			if (!isNaN(pointB.split(',')[0]) &&  !isNaN(pointB.split(',')[1])) {
				$(myParent.find('.popover-content span')[1]).css( "color", "#555555" );
			}
			else {
				$(myParent.find('.popover-content span')[1]).css( "color", "red" );
				return false;
			}
			
			return true;
		}

		myButton.click(function (event) {
			
			event.preventDefault();
			if(!$(this).prop('popShown')){
				myElement.prop('disabled', true);
				$(this).prop('popShown', true).popover('show');
				$(this).text('generate GeoJson');
				$(this).removeClass('btn-default').addClass('btn-success');
			} 
			else {
				var a = $(myParent).find('.popover-content input')[0].value.replace(/ /g, '');
				var b = $(myParent).find('.popover-content input')[1].value.replace(/ /g, '');
				
				if(validCoordinatesGiven(a,b)) {
					myElement.val( generateGeoJson(a,b) );
					myElement.prop('disabled', false);				
					$(this).prop('popShown', false).popover('hide');
					myButton.text('enter coordinates');
					$(this).removeClass('btn-success').addClass('btn-default');
				}
				
			}
			
			
			console.log("content: ", myElement.val());

			
			
		});
		  
		  
		console.log("I've been initialized for element: ", this.el);
    }
  };
});