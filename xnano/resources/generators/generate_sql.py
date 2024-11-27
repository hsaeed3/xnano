from typing import List, Optional, Union, Any, Dict, Literal
from pydantic import BaseModel, create_model

from ...lib import console, XNANOException
from ..completions.main import completion
from ...types.completions.params import (
    CompletionChatModelsParam,
    CompletionInstructorModeParam,
)
from rich.progress import Progress, SpinnerColumn, TextColumn


class SQLQuery(BaseModel):
    query: str

class SQLQueryResult(BaseModel):
    query: str
    explanation: Optional[str] = None
    dialect: str
    parameters: Optional[Dict[str, Any]] = None


def generate_sql(
    input: Union[Dict, BaseModel, List[BaseModel]],
    objective: str,
    dialect: Literal["postgresql", "mysql", "sqlite", "mssql"] = "postgresql",
    include_explanation: bool = False,
    model: Union[str, CompletionChatModelsParam] = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    mode: CompletionInstructorModeParam = "tool_call",
    temperature: float = 0.2,
    progress_bar: Optional[bool] = True,
    verbose: bool = False,
) -> SQLQueryResult:
    """
    Generates an SQL query based on input data and objective.

    Examples:
        >>> data = {"users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]}
        >>> generate_sql(data, "Get all users where id > 1")
        SQLQueryResult(
            query="SELECT * FROM users WHERE id > 1",
            explanation="This query selects all users with ID greater than 1",
            dialect="postgresql"
        )

    Args:
        input: The input data structure (dict or Pydantic model(s))
        objective: The goal or objective of the SQL query
        dialect: SQL dialect to use
        include_explanation: Whether to include query explanation
        model: The model to use for generation
        api_key: Optional API key
        base_url: Optional base URL
        organization: Optional organization ID
        mode: Completion mode
        temperature: Temperature for generation
        progress_bar: Whether to show progress bar
        verbose: Whether to show verbose output

    Returns:
        SQLQueryResult: Generated SQL query with optional explanation
    """
    
    if verbose:
        console.message(f"Generating SQL query for objective: {objective}")
        console.message(f"Using dialect: {dialect}")
        console.message(f"Input data type: {type(input)}")

    # Convert input data to a schema description
    if isinstance(input, dict):
        data_description = str(input)
    elif isinstance(input, list) and all(isinstance(x, BaseModel) for x in input):
        data_description = input[0].model_json_schema()
    elif isinstance(input, BaseModel):
        data_description = input.model_json_schema()
    else:
        raise XNANOException("Input data must be a dict, BaseModel, or List[BaseModel]")

    # Step 1: Generate the SQL query
    query_system_message = f"""
You are an expert SQL query generator. Generate a valid {dialect.upper()} SQL query based on the provided data structure and objective.

Data Structure:
{data_description}

Critical Instructions:
- Generate ONLY the SQL query text
- Follow {dialect.upper()} syntax and best practices
- Use appropriate table/column names from the provided data structure
- Ensure the query is optimized and efficient
- Do not include any DDL statements unless specifically requested
- Return only the query text, no explanation or additional text
"""

    if progress_bar:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Generating SQL query...", total=2 if include_explanation else 1)
            
            query_result = completion(
                messages=[
                    {"role": "system", "content": query_system_message},
                    {"role": "user", "content": f"Objective: {objective}"},
                ],
                model=model,
                response_model=SQLQuery,
                mode=mode,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url,
                organization=organization,
            )
            
            progress.advance(task)
            
            # Step 2: Generate explanation if requested
            explanation = None
            if include_explanation:
                explanation_system_message = """
You are an expert SQL analyst. Provide a clear, concise explanation of how the given SQL query works and what it accomplishes.

Instructions:
- Explain the query's purpose and functionality
- Highlight any important aspects or optimizations
- Keep the explanation clear and technical but accessible
- Focus on what the query does, not how to modify it
"""
                explanation_result = completion(
                    messages=[
                        {"role": "system", "content": explanation_system_message},
                        {"role": "user", "content": f"Query: {query_result.query}"},
                    ],
                    model=model,
                    response_model=create_model("Explanation", explanation=(str, ...)),
                    mode=mode,
                    temperature=temperature,
                    api_key=api_key,
                    base_url=base_url,
                    organization=organization,
                )
                explanation = explanation_result.explanation
                progress.advance(task)
    else:
        query_result = completion(
            messages=[
                {"role": "system", "content": query_system_message},
                {"role": "user", "content": f"Objective: {objective}"},
            ],
            model=model,
            response_model=SQLQuery,
            mode=mode,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
            organization=organization,
        )
        
        # Generate explanation if requested
        explanation = None
        if include_explanation:
            explanation_system_message = """
You are an expert SQL analyst. Provide a clear, concise explanation of how the given SQL query works and what it accomplishes.

Instructions:
- Explain the query's purpose and functionality
- Highlight any important aspects or optimizations
- Keep the explanation clear and technical but accessible
- Focus on what the query does, not how to modify it
"""
            explanation_result = completion(
                messages=[
                    {"role": "system", "content": explanation_system_message},
                    {"role": "user", "content": f"Query: {query_result.query}"},
                ],
                model=model,
                response_model=create_model("Explanation", explanation=(str, ...)),
                mode=mode,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url,
                organization=organization,
            )
            explanation = explanation_result.explanation

    return SQLQueryResult(
        query=query_result.query,
        explanation=explanation,
        dialect=dialect,
        parameters=None  # Could be enhanced to detect and extract parameters
    )


if __name__ == "__main__":
    print(generate_sql(
        input={"users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]},
        objective="Get all users where id > 1",
    ))
