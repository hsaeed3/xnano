__all__ = [
    "VectorStore",
    "Database"
]


from ...lib.router import router


class VectorStore(router):
    pass


VectorStore.init("xnano.resources.data.vector_store", "VectorStore")


class Database(router):
    pass


Database.init("xnano.resources.data.database", "Database")