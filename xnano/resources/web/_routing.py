__all__ = [
    "web_search",
    "web_reader",
    "web_url_search"
]


from ...lib.router import router


class web_search(router):
    pass


web_search.init("xnano.resources.web.web_searcher", "web_search")


class web_reader(router):
    pass


web_reader.init("xnano.resources.web.web_url_reader", "web_reader")


class web_url_search(router):
    pass


web_url_search.init("xnano.resources.web.web_url_searcher", "web_url_search")