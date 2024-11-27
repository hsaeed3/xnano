# full test suite for xnano

from tests.test_agents import (
    test_agents_blank_init,
    test_agents_completion_with_short_term_memory,
    test_agents_single_completion_context,
)
from tests.test_completion import (
    test_completion_defaults,
    test_completion_context,
    test_completion_string_input,
    test_completion_stream,
    test_completion_async,
    test_completion_structured_output_with_pydantic_response_model,
    test_completion_structured_output_with_instructor_mode,
    test_completion_structured_output_with_response_format,
    test_completion_structured_output_with_string_response_model,
    test_completion_structured_output_with_type_hint_response_model,
    test_completion_with_tool_execution,
    test_completion_with_tool_execution_and_returned_messages,
    test_completion_with_function_tool,
    test_completion_with_openai_function,
    test_completion_with_pydantic_model_tool,
    test_single_model_batch_job,
    test_batch_job_structured_outputs,
    test_multiple_model_batch_job,
    test_multiple_model_batch_job_structured_outputs,
)
from tests.test_generators import (
    test_generators_chunk_generation,
    test_generators_code_generation,
    test_generators_function_generator,
    test_generators_multi_label_classification,
    test_generators_single_label_classification,
    test_generators_create_qa_pairs,
    test_generators_extraction,
    test_generators_extraction_batch_inputs,
    test_generators_sql_query,
    test_generators_system_prompt,
    test_generators_validator_guardrails,
)
from tests.test_generative_model import (
    test_generative_model_init,
    test_generative_model_patch,
    test_generative_model_completion,
    test_generative_model_generate_single,
    test_generative_model_generate_multiple,
    test_generative_model_generate_single_with_messages,
    test_generative_model_field_regeneration,
)


if __name__ == "__main__":
    import pytest

    pytest.main()
