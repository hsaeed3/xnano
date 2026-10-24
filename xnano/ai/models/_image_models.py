"""
xnano.ai.models._image_models

The image generation models an [`ArtModel`][xnano.ai.models.art.ArtModel] draws pictures with:
pydantic-ai's own, by their names, and OpenRouter's, which pydantic-ai does not reach itself.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.images import (
    GeneratedImage,
    ImageGenerationModel,
    ImageGenerationResult,
    infer_image_generation_model,
)
from pydantic_ai.messages import BinaryImage

if TYPE_CHECKING:
    from pydantic_ai.images import ImageGenerationInput, ImageGenerationSettings
    from pydantic_ai.providers.openrouter import OpenRouterProvider

OPENROUTER_PREFIX = 'openrouter:'


def image_generation_model(model: ImageGenerationModel | str) -> ImageGenerationModel:
    """
    The image generation model behind a name.

    ``'openrouter:google/gemini-2.5-flash-image'`` reaches OpenRouter; any other name, such as
    ``'openai:gpt-image-1'``, is one pydantic-ai knows. A model object is returned as it is.
    """
    if isinstance(model, str):
        if model.startswith(OPENROUTER_PREFIX):
            return OpenRouterImageGenerationModel(model.removeprefix(OPENROUTER_PREFIX))
        return infer_image_generation_model(model)
    return model


class OpenRouterImageGenerationModel(ImageGenerationModel):
    """
    An image model reached through OpenRouter, whose chat completions return the picture.

    Args:
        model_name: The model, such as ``'google/gemini-2.5-flash-image'``.
        provider: The OpenRouter provider to use; ``None`` reads ``OPENROUTER_API_KEY``.
    """

    def __init__(
        self,
        model_name: str,
        *,
        provider: OpenRouterProvider | None = None,
        settings: ImageGenerationSettings | None = None,
    ) -> None:
        super().__init__(settings=settings)
        self._model_name = model_name
        self._provider = provider

    @property
    def model_name(self) -> str:
        """The model's name at OpenRouter."""
        return self._model_name

    @property
    def system(self) -> str:
        """The provider's name."""
        return 'openrouter'

    async def generate(
        self,
        prompt: str,
        *,
        images: Sequence[ImageGenerationInput] | None = None,
        settings: ImageGenerationSettings | None = None,
    ) -> ImageGenerationResult:
        """
        Ask the model for one picture of ``prompt``.

        Reference ``images`` and ``settings`` are not sent: OpenRouter's chat completions take
        the prompt alone.

        Raises:
            pydantic_ai.exceptions.UnexpectedModelBehavior: The model answered without a
                picture.
        """
        if self._provider is None:
            from pydantic_ai.providers.openrouter import OpenRouterProvider

            self._provider = OpenRouterProvider()
        response = await self._provider.client.chat.completions.create(
            model=self._model_name,
            messages=[{'role': 'user', 'content': prompt}],
            extra_body={'modalities': ['image', 'text']},
        )
        message = response.choices[0].message
        pictures = (message.model_extra or {}).get('images') or []
        if not pictures:
            answer = str(message.content)[:200]
            raise UnexpectedModelBehavior(
                f'{self._model_name} returned no picture for the prompt; its answer was '
                f'{answer!r}. Use a model that generates images, such as '
                f'google/gemini-2.5-flash-image.'
            )
        url: str = pictures[0]['image_url']['url']
        header, _, encoded = url.partition(',')
        media_type = header.removeprefix('data:').split(';', 1)[0] or 'image/png'
        content = BinaryImage(base64.b64decode(encoded), media_type=media_type)
        return ImageGenerationResult(
            images=[GeneratedImage(content)],
            prompt=prompt,
            model_name=self._model_name,
            provider_name='openrouter',
        )
