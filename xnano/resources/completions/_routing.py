__all__ = [
    "completion",
    "async_completion"
]


from ...lib.router import router


class completion(router):
    pass


completion.init("xnano.resources.completions.main", "completion")


class async_completion(router):
    pass


async_completion.init("xnano.resources.completions.main", "async_completion")