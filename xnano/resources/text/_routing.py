__all__ = [
    "text_reader",
    "text_embeddings",
    "text_chunker"
]


from ...lib.router import router


class text_reader(router):
    pass


text_reader.init("xnano.resources.text.documents.text_reader", "text_reader")


class text_embeddings(router):
    pass


text_embeddings.init("xnano.resources.text.embeddings.text_embeddings", "text_embeddings")


class text_chunker(router):
    pass

text_chunker.init("xnano.resources.text.processing.text_chunker", "text_chunker")
