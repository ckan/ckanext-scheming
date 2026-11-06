/* Enhance the schema definition textarea with a form generated from the
 * scheming meta-schema (JSON Editor).
 *
 * The textarea stays the source of truth for the POSTed value: the module
 * keeps it in sync and falls back to plain textarea editing when JSON
 * Editor is unavailable or the current content is not parseable JSON.
 */
ckan.module('scheming-schema-editor', function ($) {
  return {
    // see the list of supported languages https://germanbisurgi.github.io/jedison-docs/language-and-translations
    supportedLanguages: ['en', 'de', 'it', 'es'],
    options: {
      previewUrl: null,
      previewKind: "form",
      lang: "en"
    },
    initialize: function () {
      $.proxyAll(this, /_on/);

      if (typeof window.Jedison === 'undefined') {
        return;
      }

      this.lang = this.supportedLanguages.includes(this.options.lang) ? this.options.lang : "en";
      this.textarea = this.el.get(0);
      this.form = this.textarea.form;
      this.presets = this._loadPresets();
      this.metaSchema = JSON.parse(
        document.getElementById('scheming-meta-schema').dataset.schema
      );

      var startval = null;
      var raw = this.textarea.value.trim();

      if (raw) {
        try {
          startval = JSON.parse(raw);
        } catch (err) {
          // e.g. a form re-rendered after submitting malformed JSON:
          // keep the raw text editable instead of discarding it
          return;
        }
      }

      this._buildLayout();

      var self = this;
      this._createEditor(startval).then(function () {
        self._setFormMode(true);
        self.editor.on('change', self._onEditorChange);
        self.editor.on('instance-change', self._onInstanceChange);
        self._onEditorChange();

        self.form.addEventListener('submit', self._onSubmit);
        self.toggle.addEventListener('click', self._onToggle);
        self.textarea.addEventListener('input', self._onTextareaInput);
        self.textarea.addEventListener('paste', self._onPaste);
        if (self.previewButton) {
          self.previewButton.addEventListener('click', self._onPreview);
          self.previewClose.addEventListener('click', self._onPreviewClose);
        }
      });
    },

    _buildLayout: function () {
      this.toolbar = Object.assign(document.createElement('div'), {
        className: 'scheming-schema-editor-toolbar d-flex gap-2 py-2 mb-2'
      });

      this.toggle = Object.assign(document.createElement('button'), {
        type: 'button',
        className: 'btn btn-secondary btn-sm'
      });
      this.toolbar.appendChild(this.toggle);

      this.errorBox = Object.assign(document.createElement('div'), {
        className: 'alert alert-danger scheming-schema-editor-errors',
        hidden: true
      });

      this.editorHolder = Object.assign(document.createElement('div'), {
        className: 'scheming-schema-editor-form'
      });

      var parent = this.textarea.parentNode;
      parent.insertBefore(this.toolbar, this.textarea);
      parent.insertBefore(this.errorBox, this.textarea);
      parent.insertBefore(this.editorHolder, this.textarea);

      if (this.options.previewUrl) {
        this._buildPreviewLayout();
      }
    },

    /**
     * The preview pane lives outside the <form>, so the dataset/resource
     * inputs it contains are never submitted with the schema form.
     */
    _buildPreviewLayout: function () {
      this.previewButton = Object.assign(document.createElement('button'), {
        type: 'button',
        className: 'btn btn-secondary btn-sm',
        textContent: this.options.previewKind === 'preset'
          ? this._('Preview preset')
          : this._('Preview form')
      });
      this.toolbar.appendChild(this.previewButton);

      this.previewToolbar = Object.assign(document.createElement('div'), {
        className: 'scheming-schema-editor-toolbar py-2'
      });

      this.previewClose = Object.assign(document.createElement('button'), {
        type: 'button',
        className: 'btn btn-secondary btn-sm',
        textContent: this._('Back to editing')
      });
      this.previewToolbar.appendChild(this.previewClose);

      this.previewContent = document.createElement('div');

      this.previewPane = Object.assign(document.createElement('div'), {
        className: 'scheming-schema-preview',
        hidden: true
      });
      this.previewPane.appendChild(this.previewToolbar);
      this.previewPane.appendChild(this.previewContent);

      this.form.parentNode.insertBefore(this.previewPane, this.form.nextSibling);
    },

    /**
     * Create the Jedison editor.
     *
     * $refs in the meta-schema (label, preset, dataset_fields items, ...)
     * only resolve when a populated RefParser is passed to Jedison.Create;
     * without it every $ref-backed field renders as a type-less switcher.
     */
    _createEditor: function (startval) {
      var self = this;
      var refParser = new Jedison.RefParser();

      return refParser.dereference(this.metaSchema).then(function () {
        self.editor = new Jedison.Create({
          container: self.editorHolder,
          theme: new Jedison.ThemeBootstrap5(),
          iconLib: 'fontawesome6',
          language: self.lang,
          schema: self.metaSchema,
          refParser: refParser,
          enableCollapseToggle: true,
          enablePropertiesToggle: true,
          btnContents: false,
          switcherInput: 'modal',
          parseMarkdown: true
        });

        if (startval) {
          self.editor.setValue(startval);
        }
      });
    },

    _setFormMode: function (formMode) {
      this.formMode = formMode;
      this.textarea.hidden = formMode;
      this.editorHolder.hidden = !formMode;
      this.toggle.textContent = formMode
        ? this._('Edit as JSON/YAML')
        : this._('Edit as form');
    },

    /**
     * Parse JSON, falling back to YAML so a copy-pasted ckanext-scheming
     * YAML schema file works too. The JSON error is what gets reported
     * when both fail, since JSON is the primary expected format.
     */
    _parseDefinition: function (raw) {
      try {
        return JSON.parse(raw);
      } catch (jsonErr) {
        if (typeof window.jsyaml === 'undefined') {
          throw jsonErr;
        }

        var parsed;

        try {
          parsed = window.jsyaml.load(raw);
        } catch (yamlErr) {
          throw jsonErr;
        }

        if (parsed === undefined || parsed === null) {
          throw jsonErr;
        }

        return parsed;
      }
    },

    _onToggle: function () {
      this._clearErrors();

      if (this.formMode) {
        this.textarea.value = JSON.stringify(this.editor.getValue(), null, 2);
        this._setFormMode(false);
        return;
      }

      var parsed;
      try {
        parsed = this._parseDefinition(this.textarea.value);
      } catch (err) {
        this._showErrors([this._('Definition is not valid JSON: ') + err.message]);
        return;
      }
      this.editor.setValue(parsed);
      this._setFormMode(true);
      this._onEditorChange();
    },

    _onTextareaInput: function () {
      if (this.formMode) {
        return;
      }

      clearTimeout(this._textareaValidateTimer);
      var self = this;
      this._textareaValidateTimer = setTimeout(function () {
        self._validateTextarea();
      }, 300);
    },

    /**
     * Normalize a pasted YAML schema to JSON right away.
     */
    _onPaste: function () {
      if (this.formMode) {
        return;
      }

      var self = this;
      setTimeout(function () {
        var raw = self.textarea.value;

        try {
          JSON.parse(raw);
          return;
        } catch (err) { }

        var parsed;
        try {
          parsed = self._parseDefinition(raw);
        } catch (err) {
          return; // not valid YAML either; normal validation will flag it
        }

        self.textarea.value = JSON.stringify(parsed, null, 2);
        self._clearErrors();
      }, 0);
    },

    _validateTextarea: function () {
      var raw = this.textarea.value.trim();
      if (!raw) {
        this._clearErrors();
        return;
      }

      try {
        this._parseDefinition(raw);
      } catch (err) {
        this._showErrors(
          [this._('Definition is not valid JSON: ') + err.message],
          { scroll: false }
        );
        return;
      }
      this._clearErrors();
    },

    _validateDefinition: function () {
      if (!this.formMode) {
        var parsed;
        try {
          parsed = this._parseDefinition(this.textarea.value);
        } catch (err) {
          this._showErrors([this._('Definition is not valid JSON: ') + err.message]);
          return false;
        }
        this.textarea.value = JSON.stringify(parsed, null, 2);
        return true;
      }

      this.textarea.value = JSON.stringify(this.editor.getValue(), null, 2);

      var errors = this.editor.getErrors();

      if (errors.length) {
        this._showErrors(errors.map(function (error) {
          var path = (error.path || '').replace(/^#\/?/, '') || 'schema';
          var messages = error.messages || [error.message];
          return path + ': ' + messages.join('; ');
        }));
        return false;
      }

      return true;
    },

    _onSubmit: function (event) {
      if (!this._validateDefinition()) {
        event.preventDefault();
      }
    },

    _onPreview: function () {
      this._clearErrors();

      if (!this._validateDefinition()) {
        return;
      }

      fetch(this.options.previewUrl, {
        method: 'POST',
        body: new FormData(this.form)
      })
        .then(function (response) {
          return response.text();
        })
        .then(this._renderPreview.bind(this))
        .catch(function () {
          this._showErrors([this._('The preview could not be loaded.')]);
        }.bind(this));
    },

    _renderPreview: function (html) {
      this.previewContent.innerHTML = html;
      this.form.hidden = true;
      this.previewPane.hidden = false;

      var pending = this._loadPreviewScripts();

      return Promise.all(pending).then(function () {
        htmx_initialize_ckan_modules({
          detail: { target: this.previewContent }
        });
      }.bind(this));
    },

    _loadPreviewScripts: function () {
      this._loadedScripts = this._loadedScripts || {};

      var pending = [];

      this.previewContent.querySelectorAll('script').forEach(function (node) {
        if (node.src && this._loadedScripts[node.src]) {
          node.remove();
          return;
        }

        var script = document.createElement('script');

        if (node.src) {
          this._loadedScripts[node.src] = true;

          pending.push(new Promise(function (resolve) {
            script.onload = resolve;
            script.onerror = resolve;
            script.src = node.src;
          }));
        } else {
          script.textContent = node.textContent;
        }

        node.replaceWith(script);
      }.bind(this));

      return pending;
    },

    _onPreviewClose: function () {
      this.previewPane.hidden = true;
      this.form.hidden = false;
      this.previewContent.innerHTML = '';
    },

    _showErrors: function (messages, options) {
      var list = document.createElement('ul');
      messages.forEach(function (message) {
        var item = document.createElement('li');
        item.textContent = message;
        list.appendChild(item);
      });

      this.errorBox.innerHTML = '';
      this.errorBox.appendChild(list);
      this.errorBox.hidden = false;

      if (!options || options.scroll !== false) {
        this.errorBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    },

    _clearErrors: function () {
      this.errorBox.hidden = true;
      this.errorBox.innerHTML = '';
    },

    _loadPresets: function () {
      var el = document.getElementById('scheming-presets');
      if (!el) {
        return {};
      }
      try {
        return JSON.parse(el.dataset.presets || '{}');
      } catch (err) {
        return {};
      }
    },

    /**
     * Debounced full rescan: safety net for structural changes (array
     * item add/delete/move, initial load, JSON-mode round trip) where
     * a single instance's path doesn't tell the whole story.
     */
    _onEditorChange: function (e) {
      clearTimeout(this._presetHintsTimer);
      var self = this;

      console.log(e);
      this._presetHintsTimer = setTimeout(function () {
        self._updatePresetHints();
      }, 150);
    },

    /**
     * Targeted update fired on every 'instance-change'. Object instances
     * re-emit this event for themselves after any child changes,
     * so this fires with the field object's own path both when its
     * preset changes AND when one of its sibling properties (form_snippet,
     * etc.) is edited.
     *
     * No-op for every other path since no ".preset" node exists there.
     */
    _onInstanceChange: function (instance) {
      if (!instance || !instance.path) {
        return;
      }

      var self = this;
      var presetPath = instance.path + '/preset';

      queueMicrotask(function () {
        var presetNode = self.editorHolder.querySelector('[data-path="' + presetPath + '"]');
        if (presetNode) {
          self._renderPresetHint(presetNode);
        }
      });
    },

    _updatePresetHints: function () {
      var self = this;
      this.editorHolder.querySelectorAll('[data-path$="/preset"]').forEach(function (node) {
        self._renderPresetHint(node);
      });
    },

    /**
     * For a given "preset" field's container, show what each value the
     * selected preset would provide, and whether the field's own value
     * (set alongside the preset) is overriding it.
     */
    _renderPresetHint: function (presetNode) {
      var path = presetNode.getAttribute('data-path');
      var fieldPath = path.slice(0, -'/preset'.length);

      var presetInstance = this.editor.getInstance(path);
      var presetName = presetInstance ? presetInstance.getValue() : null;
      var presetValues = presetName && this.presets ? this.presets[presetName] : null;

      var hints = presetNode.querySelector('.scheming-preset-hints');

      if (!presetValues) {
        if (hints) {
          hints.remove();
        }
        return;
      }

      if (!hints) {
        hints = document.createElement('div');
        hints.className = 'scheming-preset-hints';
        presetNode.appendChild(hints);
      }

      hints.innerHTML = '';

      const hintsHeader = document.createElement('h4');
      hintsHeader.className = 'scheming-preset-hints-header open m-0';

      const hintsToggle = Object.assign(document.createElement('button'), {
        type: 'button',
        className: 'btn btn-link bnt-sm p-0',
        textContent: ckan.i18n._('Preset attributes:')
      });

      const hintsContent = document.createElement('div');
      hintsContent.className = 'collapse show';

      hintsHeader.appendChild(hintsToggle);
      hints.appendChild(hintsHeader);
      hints.appendChild(hintsContent);

      var collapse = new bootstrap.Collapse(hintsContent, {
        toggle: false
      });

      hintsToggle.addEventListener('click', function (e) {
        collapse.toggle();
        e.currentTarget.parentElement.classList.toggle('open');
      });

      var self = this;
      Object.keys(presetValues).sort().forEach(function (key) {
        hintsContent.appendChild(
          self._buildPresetHintRow(fieldPath, key, presetValues[key])
        );
      });
    },

    _buildPresetHintRow: function (fieldPath, key, presetValue) {
      var siblingPath = fieldPath + '/' + key;

      // DOM presence, not instance.isActive/getValue(): oneOf-wrapped
      // properties overwrite the wrapper's jedison.instances entry with
      // their branch instance, whose value survives deactivate().
      var siblingNode = this.editorHolder.querySelector('[data-path="' + siblingPath + '"]');
      var siblingInstance = siblingNode ? this.editor.getInstance(siblingPath) : null;
      var overridden = !!(siblingInstance && this._hasValue(siblingInstance.getValue()));

      var row = document.createElement('div');
      row.className = 'scheming-preset-hint';

      const label = Object.assign(document.createElement('span'), {
        className: 'scheming-preset-hint-key',
        textContent: key + ': '
      });
      row.appendChild(label);

      if (overridden) {
        row.classList.add('scheming-preset-hint-is-overridden');

        const was = Object.assign(document.createElement('del'), {
          className: 'scheming-preset-hint-value',
          textContent: this._formatPresetValue(presetValue)
        });

        row.appendChild(was);

        const now = Object.assign(document.createElement('span'), {
          className: 'scheming-preset-hint-current',
          textContent: ' ' + this._formatPresetValue(siblingInstance.getValue())
        });

        row.appendChild(now);
      } else {
        const value = Object.assign(document.createElement('span'), {
          className: 'scheming-preset-hint-value scheming-preset-hint-inherited',
          textContent: this._formatPresetValue(presetValue)
        });
        row.appendChild(value);
      }

      return row;
    },

    _hasValue: function (value) {
      if (value === undefined || value === null || value === '') {
        return false;
      }
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      if (typeof value === 'object') {
        return Object.keys(value).length > 0;
      }
      return true;
    },

    _formatPresetValue: function (value) {
      if (value === null || value === undefined || typeof value === 'string') {
        return String(value);
      }
      return JSON.stringify(value);
    }
  };
});
