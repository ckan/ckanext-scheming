from ckan.lib.helpers import lang
from pylons import config
from pylons.i18n import _

def language_text(text):
    """
    :param text: {lang: text} dict or text string

    Convert "language-text" to users' language by looking up
    languag in dict or using gettext if not a dict
    """
    if hasattr(t, 'get'):
        l = lang()
        v = text.get(l)
        if not v:
            v = text.get(config.get('ckan.locale_default', 'en'))
            if not v:
                l, v = sorted(text.items())[0]
        return v
    else:
        return _(text)
