from flask import request, url_for
from werkzeug.routing import BaseConverter


def active_if(var, value, class_alone=True):
    """
    Returns 'active' if var equals value, else empty string
    """
    if var == value:
        return 'active' if class_alone else ' active'
    return ''


def url_for_page(page):
    """
    Creates url for specific page
    """
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def register(app):
    app.add_template_filter(url_for_page)
    app.add_template_filter(active_if)
    app.url_map.converters['regex'] = RegexConverter