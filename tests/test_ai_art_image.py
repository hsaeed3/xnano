"""
tests.test_ai_art_image

Pixel art read out of a picture an image model drew, and the image models ArtModel reaches.
"""

from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest

pytest.importorskip('pydantic_ai')

from pydantic_ai.exceptions import UnexpectedModelBehavior  # noqa: E402
from pydantic_ai.images import (  # noqa: E402
    GeneratedImage,
    ImageGenerationModel,
    ImageGenerationResult,
)
from pydantic_ai.messages import BinaryImage  # noqa: E402
from xnano_image import TerminalImage  # noqa: E402

from xnano.ai import ArtModel, ArtText, PaletteColor  # noqa: E402
from xnano.ai.models._art_pixelize import pixelize  # noqa: E402
from xnano.ai.models._image_models import (  # noqa: E402
    OpenRouterImageGenerationModel,
    image_generation_model,
)
from xnano.ai.models.art import _png_of  # noqa: E402

COIN = ArtText(
    rows=(
        '........',
        '..oooo..',
        '.oyyyyo.',
        '.oyhyyo.',
        '.oyyyso.',
        '.oyyyso.',
        '..oooo..',
        '........',
    ),
    palette={
        'o': PaletteColor('outline', '#1a1c2c'),
        'y': PaletteColor('base', '#ffcd75'),
        'h': PaletteColor('highlight', '#fff3b0'),
        's': PaletteColor('shadow', '#b86f50'),
    },
)


def picture_of(text: ArtText) -> TerminalImage:
    """A picture in the pixel-art style: the art scaled up on a flat ground."""
    return TerminalImage.from_bytes(_png_of(text))


class PicturedModel(ImageGenerationModel):
    """An image model that answers every prompt with one fixed picture."""

    def __init__(self, data: bytes) -> None:
        super().__init__()
        self.data = data
        self.prompts: list[str] = []

    @property
    def model_name(self) -> str:
        return 'pictured'

    @property
    def system(self) -> str:
        return 'test'

    async def generate(self, prompt, *, images=None, settings=None):  # type: ignore[override]
        self.prompts.append(prompt)
        return ImageGenerationResult(
            images=[GeneratedImage(BinaryImage(self.data, media_type='image/png'))],
            prompt=prompt,
            model_name='pictured',
            provider_name='test',
        )


class TestPixelize:
    def test_the_sprite_is_read_back_pixel_for_pixel(self):
        found = pixelize(picture_of(COIN), widths=(1, 32), heights=(1, 32), most_colors=8)
        colors = dict(found.palette)
        # the ground is keyed out and the sprite cropped to its 6 by 6 bounds
        assert (len(found.rows[0]), len(found.rows)) == (6, 6)
        assert found.shrink == 1
        assert found.pitch == 32  # 256 pixels for art 8 wide
        drawn = tuple(row[1:7] for row in COIN.rows[1:7])
        read = tuple(
            ''.join(
                '.'
                if letter == '.'
                else next(k for k, v in COIN.palette.items() if v.color == colors[letter])
                for letter in row
            )
            for row in found.rows
        )
        assert read == drawn

    def test_a_large_sprite_is_shrunk_by_a_whole_factor(self):
        big = ArtText(
            tuple('o' * 16 for _ in range(16)), {'o': PaletteColor('base', '#38b764')}
        )
        bordered = ArtText(
            ('.' * 18, *(f'.{row}.' for row in big.rows), '.' * 18), dict(big.palette)
        )
        found = pixelize(
            picture_of(bordered), widths=(1, 8), heights=(1, 8), most_colors=4
        )
        assert found.shrink == 2
        assert (len(found.rows[0]), len(found.rows)) == (8, 8)

    def test_a_picture_of_only_background_is_refused(self):
        blank = ArtText(
            ('....', '....', '....', '....'), {'o': PaletteColor('base', '#000000')}
        )
        with pytest.raises(ValueError, match='no sprite on its background'):
            pixelize(picture_of(blank), widths=(1, 8), heights=(1, 8), most_colors=4)


class TestImageModels:
    def test_names_resolve_to_models(self):
        model = image_generation_model('openrouter:google/gemini-2.5-flash-image')
        assert isinstance(model, OpenRouterImageGenerationModel)
        assert model.model_name == 'google/gemini-2.5-flash-image'
        assert model.system == 'openrouter'
        pictured = PicturedModel(b'')
        assert image_generation_model(pictured) is pictured

    @pytest.mark.anyio
    async def test_the_openrouter_picture_is_read_from_its_data_url(self):
        data = _png_of(COIN)
        url = 'data:image/png;base64,' + base64.b64encode(data).decode()

        class Completions:
            async def create(self, **arguments):
                self.arguments = arguments
                message = SimpleNamespace(
                    content='Here it is.',
                    model_extra={'images': [{'image_url': {'url': url}}]},
                )
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        completions = Completions()
        provider = SimpleNamespace(
            client=SimpleNamespace(chat=SimpleNamespace(completions=completions))
        )
        model = OpenRouterImageGenerationModel(
            'google/gemini-2.5-flash-image', provider=provider
        )  # type: ignore[arg-type]
        result = await model.generate('a coin')
        assert result.images[0].content.data == data
        assert result.images[0].content.media_type == 'image/png'
        assert completions.arguments['extra_body'] == {'modalities': ['image', 'text']}

    @pytest.mark.anyio
    async def test_an_answer_without_a_picture_is_an_error(self):
        class Completions:
            async def create(self, **arguments):
                message = SimpleNamespace(content='I cannot draw.', model_extra={})
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        provider = SimpleNamespace(
            client=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
        )
        model = OpenRouterImageGenerationModel(
            'google/gemini-2.5-flash-image', provider=provider
        )  # type: ignore[arg-type]
        with pytest.raises(UnexpectedModelBehavior, match='returned no picture'):
            await model.generate('a coin')


class TestArtModelWithPictures:
    def test_generate_draws_the_picture_and_reads_it(self):
        pictured = PicturedModel(_png_of(COIN))
        artist = ArtModel(image_model=pictured, width=(1, 16), height=(1, 16))
        art = artist.generate('a gold coin')
        assert (art.width, art.height) == (6, 6)
        assert art.pixel(2, 1)[:3] == (255, 205, 117)
        report = artist.last_generation
        assert report.strategy == 'image' and report.attempts == 1
        assert any('picture pixels wide' in note for note in report.notes)
        assert 'pixel art sprite of a gold coin' in pictured.prompts[0]
        assert '16 by 16 pixels' in pictured.prompts[0]

    def test_a_picture_without_a_sprite_is_a_generation_error(self):
        from xnano.ai import GenerationError

        blank = ArtText(
            ('....', '....', '....', '....'), {'o': PaletteColor('base', '#000000')}
        )
        artist = ArtModel(image_model=PicturedModel(_png_of(blank)), width=8, height=8)
        with pytest.raises(GenerationError, match='no sprite on its background'):
            artist.generate('nothing')
