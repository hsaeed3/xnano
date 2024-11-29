__all__ = [
    "VectorStore",
    "Database",
    "web_reader",
    "web_search",
    "web_news_search",
    "async_web_search",
    "async_web_news_search",
    "async_web_reader",
]


from ...lib.router import router


class VectorStore(router):
    pass


VectorStore.init("xnano.resources.data.vector_store", "VectorStore")


class Database(router):
    pass


Database.init("xnano.resources.data.database", "Database")


class web_reader(router):
    pass


web_reader.init("xnano.resources.data.web", "web_reader")


class web_search(router):
    pass


web_search.init("xnano.resources.data.web", "web_search")


class web_news_search(router):
    pass


web_news_search.init("xnano.resources.data.web", "web_news_search")


class async_web_search(router):
    pass


async_web_search.init("xnano.resources.data.web", "async_web_search")


class async_web_news_search(router):
    pass


async_web_news_search.init("xnano.resources.data.web", "async_web_news_search")


class async_web_reader(router):
    pass


async_web_reader.init("xnano.resources.data.web", "async_web_reader")
