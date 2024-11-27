from ..completions.main import completion
from pydantic import BaseModel, create_model
from typing import List, Optional, Union, Literal
from ..text.processing.text_chunker import text_chunker


class Chunk(BaseModel):
    text: str
    context: str
    

def generate_chunks(
    inputs: Union[str, List[str]],
    enhancement_type: Literal["summary", "context"] = "context",
    chunk_size: int = 512,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    progress_bar: bool = True,
) -> Union[List[str], List[List[str]]]:
    """
    Generates semantically enhanced chunks with either summaries or context strings.
    
    Args:
        inputs: Text(s) to chunk and enhance
        enhancement_type: Type of enhancement ("summary" or "context")
        chunk_size: Target size for each chunk in tokens
        model: LLM model to use for enhancement
        api_key: Optional API key for the LLM
        base_url: Optional base URL for API
        progress_bar: Show progress bar if True
    
    Returns:
        Enhanced chunks with context or summaries
    """
    # First, generate regular chunks
    raw_chunks = text_chunker(
        inputs,
        chunk_size=chunk_size,
        progress_bar=progress_bar
    )

    if isinstance(inputs, str):
        single_input = True
        chunks_list = [raw_chunks]
    else:
        single_input = False
        chunks_list = raw_chunks

    enhanced_results = []

    # System messages for different enhancement types
    system_messages = {
        "summary": """You are an expert at summarizing text chunks. Create a brief, informative summary that captures the key points of each chunk.""",
        "context": """You are an expert at understanding text context. For each chunk, generate a brief contextual description that helps understand its role in the larger document."""
    }

    for chunks in chunks_list:
        enhanced_chunks = []
        
        for chunk in chunks:
            # Create prompt based on enhancement type
            if enhancement_type == "summary":
                user_message = f"Please provide a concise summary of this text chunk:\n\n{chunk}"
            else:  # context
                user_message = f"Please provide a brief contextual description for this text chunk:\n\n{chunk}"

            # Use completion similar to classifier.py
            result = completion(
                messages=[
                    {"role": "system", "content": system_messages[enhancement_type]},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                response_model=create_model("Enhancement", content=(str, ...)),
                mode="tool_call",
                api_key=api_key,
                base_url=base_url
            )

            enhanced_chunks.append(
                Chunk(
                    text=chunk,
                    context=result.content
                )
            )

        # Convert Chunk objects to strings before adding to results
        formatted_chunks = [f"{chunk.text}\n[{enhancement_type}: {chunk.context}]" for chunk in enhanced_chunks]
        enhanced_results.append(formatted_chunks)

    return enhanced_results[0] if single_input else enhanced_results