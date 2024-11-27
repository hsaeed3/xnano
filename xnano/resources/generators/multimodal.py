from typing import Literal, Optional, Any, Union
from ...lib import console


__all__ = ["image", "audio", "transcribe"]


def prompt_cli_install(library: str):
    """Installs a specified library"""

    import os

    os.system(f"pip install {library}")


ModelType = Literal[
    "dall-e-2",
    "dall-e-3",
    "flux-dev",
    "flux-realism",
    "flux-schnell",
    "flux-pro",
    "flux-lora",
    "flux-general",
    "aura",
    "sd-v3",
    "fooocus",
]

PREDEFINED_APPS: Literal[
    "fal-ai/flux/dev",
    "fal-ai/flux-realism",
    "fal-ai/flux/schnell",
    "fal-ai/flux-pro",
    "fal-ai/flux-lora",
    "fal-ai/flux-general",
    "fal-ai/aura-flow",
    "fal-al/lora",
    "fal-ai/stable-diffusion-v3-medium",
    "fal-ai/fooocus",
] = None


def _get_model_config(model: ModelType):
    dall_e_models = ["dall-e-2", "dall-e-3"]
    fal_models = {
        "flux-dev": "fal-ai/flux/dev",
        "flux-realism": "fal-ai/flux-realism",
        "flux-schnell": "fal-ai/flux/schnell",
        "flux-pro": "fal-ai/flux-pro",
        "flux-lora": "fal-ai/flux-lora",
        "flux-general": "fal-ai/flux-general",
        "aura": "fal-ai/aura-flow",
        "sd-v3": "fal-ai/stable-diffusion-v3-medium",
        "fooocus": "fal-ai/fooocus",
    }

    if model in dall_e_models:
        return {"provider": "openai", "model": model}
    elif model in fal_models:
        return {"provider": "fal", "application": fal_models[model]}
    else:
        raise ValueError(f"Unsupported model: {model}")


def multimodal_generate_image(
    prompt: str,
    model: ModelType = "dall-e-3",
    api_key: Optional[str] = None,
    image_size: Optional[str] = "landscape_4_3",
    num_inference_steps: Optional[int] = 26,
    guidance_scale: Optional[float] = 3.5,
    enable_safety_checker: Optional[bool] = False,
    size: Optional[str] = "1024x1024",
    quality: Optional[str] = "standard",
    n: Optional[int] = 1,
    display: Optional[bool] = False,
    optimize_prompt: Optional[bool] = False,
    optimize_prompt_model: Optional[str] = "openai/gpt-4o-mini",
) -> Union[str, Any]:
    """Generates an image using either the FAL_AI API or OpenAI. With an
    optional display function to show the image in a notebook.

    Parameters:
        prompt: str,
        model: ModelType = "dall-e-3",
        api_key: Optional[str] = None,
        image_size: Optional[str] = "landscape_4_3",
        num_inference_steps: Optional[int] = 26,
        guidance_scale: Optional[float] = 3.5,
        enable_safety_checker: Optional[bool] = False,
        size: Optional[str] = "1024x1024",
        quality: Optional[str] = "standard",
        n: Optional[int] = 1,
        display: Optional[bool] = False,

    Returns:
        str or Any: The generated image or an error message.
    """
    model_config = _get_model_config(model)

    if model_config["provider"] == "openai":
        from openai import OpenAI

        try:
            client = OpenAI(api_key=api_key)
        except Exception as e:
            return e
        try:
            response = client.images.generate(
                model=model_config["model"],
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
            )
        except Exception as e:
            return e
        if display:
            try:
                from IPython.display import display, Image
            except ImportError:
                console.warning(
                    "IPython is not installed. Please install it with `pip install ipython`."
                )
                prompt_cli_install("IPython")

            url = response.data[0].url
            display(Image(url=url))
        return response

    elif model_config["provider"] == "fal":
        try:
            import fal_client
        except ImportError:
            console.critical(
                "FAL_AI API requires the 'fal-client' package. Please install it with `pip install fal-client`."
            )
            prompt_cli_install("fal-client")

        if optimize_prompt:
            from ..completions.main import completion
            from pydantic import BaseModel

            class OptimizedPrompt(BaseModel):
                prompt: str

            optimized_prompt = completion(
                messages=[
                    {
                        "role": "system",
                        "content": f"""
                 ## CONTEXT ## \n
                 You are a world class image description optimizer. You enhance descriptions of images at incredible quality, detail, but with a focus on being concise. You define your descritpions
                 in a comma list of 2-3 word phrases. \n\n
                 
                 ## INSTRUCTIONS ## \n
                 - You will be given a description of an image
                 - Reason about the image as a whole, and descriptions the user has provided
                 - Optimize the prompt for use in image generation
                 - Ensure that the optimized prompt is a concise, detailed list of 2-3 word phrases.
                 
                 ## EXAMPLE ## \n
                 Original Prompt : [ A beautiful landscape painting of a sunset over the ocean. ] \n
                 Optimized Prompt : [ A beautiful painting, pink vibrant sunset, dynamic ocean waves, vibrant art, 4k, brush strokes ]
                 
                 """,
                    },
                    {
                        "role": "user",
                        "content": f"Optimize this image description for use in image generation. The original prompt is : [ {prompt} ]",
                    },
                ],
                model=optimize_prompt_model,
                response_model=OptimizedPrompt,
            )

            prompt = optimized_prompt.prompt

        try:
            handler = fal_client.submit(
                application=model_config["application"],
                arguments={
                    "prompt": prompt,
                    "image_size": image_size,
                    "num_inference_steps": num_inference_steps,
                    "guidance_scale": guidance_scale,
                    "enable_safety_checker": enable_safety_checker,
                    "num_images": n,
                },
            )
            result = handler.get()
            if display:
                try:
                    from IPython.display import display, Image
                except ImportError:

                    console.warning(
                        "IPython is not installed. Please install it with `pip install ipython`."
                    )
                    prompt_cli_install("IPython")

                url = result["images"][0]["url"]
                display(Image(url=url))
        except Exception as e:
            result = e
        return result


OPENAI_TTS_MODELS = Literal["tts-1", "tts-1-hd"]
OPENAI_TTS_VOICES = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


def multimodal_generate_audio(
    prompt: str,
    model: OPENAI_TTS_MODELS = "tts-1",
    voice: OPENAI_TTS_VOICES = "alloy",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    filename: Optional[str] = None,
    play: bool = False,
):
    """Generates an audio file from text, through the openai API.

    Parameters:
        prompt: str,
        model: OPENAI_TTS_MODELS = "tts-1",
        voice: OPENAI_TTS_VOICES = "alloy",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        filename: Optional[str] = None,
        play: bool = False,

    Returns:
        str or Any: The generated audio file or an error message.
    """
    from openai import OpenAI
    import io

    try:
        import sounddevice as sd
        import soundfile as sf

    except ImportError:

        console.warning(
            "The [italic]speak[/italic] function requires sounddevice and soundfile, which are not included in the base 'xnano' package. Please install them with [bold]`pip install sounddevice soundfile`[/bold]."
        )
        prompt_cli_install("sounddevice soundfile")

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.audio.speech.create(input=prompt, model=model, voice=voice)
        audio_data = response.read()

        try:
            with io.BytesIO(audio_data) as audio_buffer:
                audio_array, sample_rate = sf.read(audio_buffer)
        except Exception as e:
            return e

        if filename:
            file_endings = [".wav", ".mp3", ".m4a"]
            if not filename.endswith(tuple(file_endings)):
                raise ValueError(
                    f"Filename must end with one of the following: {', '.join(file_endings)}"
                )

            sf.write(filename, audio_array, sample_rate)

        if play:
            try:
                from IPython.display import Audio
            except ImportError:

                console.warning(
                    "IPython is not installed. Please install it with `pip install ipython`."
                )
                prompt_cli_install("IPython")
            # Play audio using sounddevice
            sd.play(audio_array, sample_rate)
            sd.wait()

            # For Jupyter notebook, also return IPython audio widget
            return Audio(audio_array, rate=sample_rate, autoplay=True)
        else:
            return audio_array, sample_rate

    except Exception as e:
        return str(e)


def multimodal_generate_transcription(
    model: str = "whisper-1",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    organization: Optional[str] = None,
    file: Optional[str] = None,
    record: bool = False,
    duration: int = 5,
):
    """Transcribes an audio file into text, through the openai API.

    Parameters:
        model: str = "whisper-1",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        file: Optional[str] = None,
        record: bool = False,
        duration: int = 5,

    Returns:
        str or Any: The transcribed text or an error message.
    """
    from openai import OpenAI

    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:

        console.warning(
            "The [italic]speak[/italic] function requires sounddevice and soundfile, which are not included in the base 'xnano` package. Please install them with [bold]`pip install sounddevice soundfile`[/bold]."
        )
        prompt_cli_install("sounddevice soundfile")

    import io

    client = OpenAI(api_key=api_key, base_url=base_url, organization=organization)

    if record:
        print(f"Recording for {duration} seconds...")
        audio_data = sd.rec(int(duration * 44100), samplerate=44100, channels=1)
        sd.wait()
        print("Recording finished.")

        with io.BytesIO() as buffer:
            sf.write(buffer, audio_data, 44100, format="wav")
            buffer.seek(0)
            audio_file = buffer
    elif file:
        if not file.endswith((".mp3", ".wav", ".m4a")):
            raise ValueError("File must be a .mp3, .wav, or .m4a file")
        audio_file = open(file, "rb")
    else:
        raise ValueError(
            "Either 'file' must be provided or 'record' must be set to True"
        )

    try:
        transcription = client.audio.transcriptions.create(
            model=model, file=audio_file, response_format="text"
        )
        return transcription
    except Exception as e:
        return str(e)


class MultimodalClient:
    @staticmethod
    def multimodal_generate_image(
        prompt: str,
        model: ModelType = "dall-e-3",
        api_key: Optional[str] = None,
        image_size: Optional[str] = "landscape_4_3",
        num_inference_steps: Optional[int] = 26,
        guidance_scale: Optional[float] = 3.5,
        enable_safety_checker: Optional[bool] = False,
        size: Optional[str] = "1024x1024",
        quality: Optional[str] = "standard",
        n: Optional[int] = 1,
        display: Optional[bool] = False,
        optimize_prompt: Optional[bool] = False,
        optimize_prompt_model: Optional[str] = "openai/gpt-4o-mini",
    ):
        return multimodal_generate_image(
            prompt=prompt,
            model=model,
            api_key=api_key,
            image_size=image_size,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            enable_safety_checker=enable_safety_checker,
            size=size,
            quality=quality,
            n=n,
            display=display,
            optimize_prompt=optimize_prompt,
            optimize_prompt_model=optimize_prompt_model,
        )

    @staticmethod
    def multimodal_generate_audio(
        prompt: str,
        model: OPENAI_TTS_MODELS = "tts-1",
        voice: OPENAI_TTS_VOICES = "alloy",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        filename: Optional[str] = None,
        play: bool = False,
    ):
        return multimodal_generate_audio(
            prompt=prompt,
            model=model,
            voice=voice,
            api_key=api_key,
            base_url=base_url,
            filename=filename,
            play=play,
        )

    @staticmethod
    def multimodal_generate_transcription(
        model: str = "whisper-1",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        file: Optional[str] = None,
        record: bool = False,
        duration: int = 5,
    ):
        return multimodal_generate_transcription(
            model=model,
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            file=file,
            record=record,
            duration=duration,
        )


if __name__ == "__main__":
    print(
        multimodal_generate_image(
            model="flux-dev",
            prompt="A beautiful landscape painting of a sunset over the ocean.",
            n=1,
        )
    )
