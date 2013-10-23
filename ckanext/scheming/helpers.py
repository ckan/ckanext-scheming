from ckan.lib.helpers import lang
from pylons import config
from pylons.i18n import gettext

def scheming_language_text(text):
    """
    :param text: {lang: text} dict or text string

    Convert "language-text" to users' language by looking up
    languag in dict or using gettext if not a dict
    """
    if hasattr(text, 'get'):
        l = lang()
        v = text.get(l)
        if not v:
            v = text.get(config.get('ckan.locale_default', 'en'))
            if not v:
                # just give me something to display
                l, v = sorted(text.items())[0]
        return v
    else:
        return gettext(text)
