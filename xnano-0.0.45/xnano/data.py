__all__ = [
    # documents & methods
    "text_reader",
    # nlp
    "text_chunker",
    # web
    "web_search",
    "web_reader",
    "web_url_search",
    "web_scraper",
    # embeddings
    "generate_embeddings",
    # database
    "Database",
    # vectors & embeddings
    "VectorStore",
]


from ._lib.router import router


class text_reader(router):
    pass

text_reader.init("xnano.resources.data.documents.read_documents", "read_documents")


class text_chunker(router):
    pass

text_chunker.init("xnano.resources.data.nlp.chunker", "text_chunker")


class Database(router):
    pass

Database.init("xnano.resources.data.database.main", "Database")


class VectorStore(router):
    pass

VectorStore.init("xnano.resources.data.embeddings.vector_store", "VectorStore")


class generate_embeddings(router):
    pass

generate_embeddings.init("xnano.resources.data.embeddings.embedder", "generate_embeddings")


class web_scraper(router):
    pass

web_scraper.init("xnano.resources.data.web.web_scraper", "web_scraper")


class web_reader(router):
    pass    

web_reader.init("xnano.resources.data.web.web_url_reader", "web_reader")


class web_url_search(router):
    pass

web_url_search.init("xnano.resources.data.web.web_url_searcher", "web_url_search")


class web_search(router):
    pass

web_search.init("xnano.resources.data.web.web_searcher", "web_search")


