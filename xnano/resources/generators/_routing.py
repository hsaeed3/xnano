__all__ = [
    "generate_code",
    "generate_function",
    "generate_classification",
    "async_generate_classification",
    "generate_chunks",
    "generate_extraction",
    "async_generate_extraction",
    "generate_sql",
    "generate_system_prompt",
    "generate_qa_pairs",
    "generate_answers",
    "generate_questions",
    "generate_validation",
    "async_generate_validation",
    "generate_web_extraction",

    # multimodal
    "multimodal_generate_image",
    "multimodal_generate_audio",
    "multimodal_generate_transcription",
]


from ...lib.router import router


class generate_code(router):
    pass


generate_code.init("xnano.resources.generators.code_generators", "generate_code")


class generate_function(router):
    pass


generate_function.init("xnano.resources.generators.code_generators", "generate_function")


class generate_classification(router):
    pass


generate_classification.init("xnano.resources.generators.classifier", "generate_classification")


class async_generate_classification(router):
    pass


async_generate_classification.init("xnano.resources.generators.classifier", "async_generate_classification")


class generate_chunks(router):
    pass


generate_chunks.init("xnano.resources.generators.chunker", "generate_chunks")


class generate_extraction(router):
    pass


generate_extraction.init("xnano.resources.generators.extractor", "generate_extraction")


class async_generate_extraction(router):
    pass


async_generate_extraction.init("xnano.resources.generators.extractor", "async_generate_extraction")


class generate_sql(router):
    pass


generate_sql.init("xnano.resources.generators.sql_generator", "generate_sql")


class generate_system_prompt(router):
    pass


generate_system_prompt.init("xnano.resources.generators.prompting", "generate_system_prompt")


class generate_qa_pairs(router):
    pass


generate_qa_pairs.init("xnano.resources.generators.question_answer", "generate_qa_pairs")


class generate_answers(router):
    pass


generate_answers.init("xnano.resources.generators.question_answer", "generate_answers")


class generate_questions(router):
    pass


generate_questions.init("xnano.resources.generators.question_answer", "generate_questions")


class generate_validation(router):
    pass


generate_validation.init("xnano.resources.generators.validator", "generate_validation")


class async_generate_validation(router):
    pass


async_generate_validation.init("xnano.resources.generators.validator", "async_generate_validation")


class generate_web_extraction(router):
    pass


generate_web_extraction.init("xnano.resources.generators.web_extractor", "generate_web_extraction")


class multimodal_generate_image(router):
    pass


multimodal_generate_image.init("xnano.resources.generators.multimodal", "multimodal_generate_image")


class multimodal_generate_audio(router):
    pass


multimodal_generate_audio.init("xnano.resources.generators.multimodal", "multimodal_generate_audio")


class multimodal_generate_transcription(router):
    pass


multimodal_generate_transcription.init("xnano.resources.generators.multimodal", "multimodal_generate_transcription")
