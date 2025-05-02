ckan.module('scheming-suggestions', function($) {
    return {
      initialize: function() {
        console.log("Initializing scheming-suggestions module");
        
        var el = this.el;
        var content = $(el).attr('data-content');
        
        var $popoverDiv = $('<div class="custom-suggestion-popover" style="display: none;"></div>');
        $popoverDiv.html(content);
        $('body').append($popoverDiv);
        
        $(el).closest('.control-group').addClass('has-suggestion');
        
        $popoverDiv.find('.suggestion-apply-btn').each(function() {
          var isValid = $(this).data('is-valid') !== 'false';
          if (!isValid) {
            $(this).addClass('suggestion-apply-btn-disabled');
          }
        });
        
        $(el).on('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          
          $('.custom-suggestion-popover').hide();
          
          var buttonPos = $(el).offset();
          var parentWidth = $(window).width();
          var popoverWidth = Math.min(350, parentWidth - 40);
          
          var leftPos = buttonPos.left;
          if (leftPos + popoverWidth > parentWidth - 20) {
            leftPos = Math.max(20, parentWidth - popoverWidth - 20);
          }
          
          $popoverDiv.css({
            position: 'absolute',
            top: buttonPos.top + $(el).outerHeight() + 10,
            left: leftPos,
            maxWidth: popoverWidth + 'px',
            zIndex: 1000
          });
          
          $popoverDiv.toggle();
        });
        
        // Close popover when clicking outside
        $(document).on('click', function(e) {
          if (!$(e.target).closest('.suggestion-btn').length && 
              !$(e.target).closest('.custom-suggestion-popover').length) {
            $popoverDiv.hide();
          }
        });
        
        // Handle formula toggle button
        $popoverDiv.on('click', '.formula-toggle-btn', function(e) {
          e.preventDefault();
          e.stopPropagation();
          
          var $formulaSection = $(this).closest('.suggestion-popover-content').find('.suggestion-formula');
          var $toggleIcon = $(this).find('.formula-toggle-icon');
          var $toggleText = $(this).find('.formula-toggle-text');
          
          if ($formulaSection.is(':visible')) {
            // Hide formula
            $formulaSection.slideUp(200);
            $toggleIcon.html('&#9660;'); // Down arrow
            $toggleText.text('Show formula');
            $(this).removeClass('formula-toggle-active');
          } else {
            // Show formula
            $formulaSection.slideDown(200);
            $toggleIcon.html('&#9650;'); // Up arrow
            $toggleText.text('Hide formula');
            $(this).addClass('formula-toggle-active');
          }
        });
        
        // Handle copy formula button
        $popoverDiv.on('click', '.copy-formula-btn', function(e) {
          e.preventDefault();
          e.stopPropagation();
          
          var formula = $(this).data('formula');
          var $copyBtn = $(this);
          
          // Create a temp textarea to copy from
          var $temp = $("<textarea>");
          $("body").append($temp);
          $temp.val(formula).select();
          
          try {
            // Execute copy command
            var successful = document.execCommand('copy');
            
            if (successful) {
              // Show success state
              $copyBtn.addClass('copy-success');
              
              // Store original content
              var $icon = $copyBtn.find('svg');
              var originalHtml = $icon.html();
              
              // Show checkmark
              $icon.html('<path d="M20 6L9 17l-5-5"></path>');
              
              // Reset after 2 seconds
              setTimeout(function() {
                $copyBtn.removeClass('copy-success');
                $icon.html(originalHtml);
              }, 2000);
            }
          } catch (err) {
            console.error('Could not copy formula: ', err);
          }
          
          // Remove temp textarea
          $temp.remove();
        });
        
        // Handle apply suggestion button
        $popoverDiv.on('click', '.suggestion-apply-btn', function(e) {
          e.preventDefault();
          e.stopPropagation();
          
          // Skip if button is disabled
          if ($(this).hasClass('suggestion-apply-btn-disabled')) {
            console.log("Ignoring click on disabled apply button");
            return;
          }
          
          var targetId = $(this).data('target');
          var suggestionValue = $(this).data('value');
          var isSelectField = $(this).data('is-select') === 'true';
          var isValid = $(this).data('is-valid') !== 'false'; // Default to true if not specified
          var $target = $('#' + targetId);
          
          if ($target.length === 0) {
            console.error("Target not found:", targetId);
            return;
          }
          
          console.log("Applying suggestion to", targetId);
          
          // Handle different input types
          if ($target.is('textarea')) {
            $target.val(suggestionValue);
            // If it's a markdown editor, also update the preview
            if ($target.hasClass('markdown-editor')) {
              $target.trigger('change');
            }
          } else if ($target.is('input[type="text"]')) {
            $target.val(suggestionValue);
          } else if ($target.is('select')) {
            if (isValid) {
              $target.val(suggestionValue);
              $target.trigger('change');
            } else {
              var $warningMsg = $('<div class="suggestion-warning-message">The suggested value is not a valid option</div>');
              $warningMsg.css({
                position: 'absolute',
                top: $target.offset().top - 25,
                left: $target.offset().left + $target.outerWidth() / 2,
                transform: 'translateX(-50%)',
                backgroundColor: '#e67e22',
                color: 'white',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 'bold',
                zIndex: 1010,
                opacity: 0,
                transition: 'opacity 0.3s ease'
              });
              $('body').append($warningMsg);
              
              setTimeout(function() {
                $warningMsg.css('opacity', '1');
              }, 10);
              
              setTimeout(function() {
                $warningMsg.css('opacity', '0');
                setTimeout(function() {
                  $warningMsg.remove();
                }, 300);
              }, 3000);
              
              $target.addClass('suggestion-invalid');
              setTimeout(function() {
                $target.removeClass('suggestion-invalid');
              }, 3000);
              
              // Hide the popover
              $popoverDiv.hide();
              return;
            }
          }
          
          // Add a success class for animation
          $target.addClass('suggestion-applied');
          setTimeout(function() {
            $target.removeClass('suggestion-applied');
          }, 1000);
          
          // Show a brief success message
          var $successMsg = $('<div class="suggestion-success-message">Suggestion applied!</div>');
          $successMsg.css({
            position: 'absolute',
            top: $target.offset().top - 25,
            left: $target.offset().left + $target.outerWidth() / 2,
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(42, 145, 52, 0.9)',
            color: 'white',
            padding: '4px 10px',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 'bold',
            zIndex: 1010,
            opacity: 0,
            transition: 'opacity 0.3s ease'
          });
          $('body').append($successMsg);
          
          setTimeout(function() {
            $successMsg.css('opacity', '1');
          }, 10);
          
          setTimeout(function() {
            $successMsg.css('opacity', '0');
            setTimeout(function() {
              $successMsg.remove();
            }, 300);
          }, 1500);
          
          // Hide the popover
          $popoverDiv.hide();
        });
      }
    };
  });