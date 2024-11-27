# xnano
# hammad saeed // 2024

# main exports

__all__ = [
    # completions // no client
    "completion",
    "acompletion",
    # methods
    "generate_code",
    "generate_chunks",
    "function",
    "generate_sql",
    "generate_system_prompt",
    "generate_qa_pairs",
    "validate",
    "avalidate",
    "classify",
    "aclassify",
    "extract",
    "aextract",
]

# imports

from ._lib.router import router


class completion(router):
    pass

completion.init("xnano.resources.completions.main", "completion")


class acompletion(router):
    pass

acompletion.init("xnano.resources.completions.main", "acompletion")


class classify(router):
    pass

classify.init("xnano.resources.completions.classifier", "classify")


class aclassify(router):
    pass

aclassify.init("xnano.resources.completions.classifier", "aclassify")


class extract(router):
    pass

extract.init("xnano.resources.completions.extractor", "extract")


class aextract(router):
    pass

aextract.init("xnano.resources.completions.extractor", "aextract")


class function(router):
    pass

function.init("xnano.resources.completions.code_generators", "function")


class generate_chunks(router):
    pass

generate_chunks.init("xnano.resources.completions.chunker", "generate_chunks")


class generate_code(router):
    pass

generate_code.init("xnano.resources.completions.code_generators", "generate_code")


class generate_sql(router):
    pass

generate_sql.init("xnano.resources.completions.generate_sql", "generate_sql")


class generate_system_prompt(router):
    pass

generate_system_prompt.init("xnano.resources.completions.prompting", "generate_system_prompt")


class generate_qa_pairs(router):
    pass

generate_qa_pairs.init("xnano.resources.completions.question_answer", "generate_qa_pairs")  


class validate(router):
    pass

validate.init("xnano.resources.completions.validator", "validate")


class avalidate(router):
    pass

avalidate.init("xnano.resources.completions.validator", "avalidate")
