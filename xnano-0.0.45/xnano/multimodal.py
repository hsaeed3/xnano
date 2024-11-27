__all__ = [
    "generate_image",
    "generate_audio",
    "generate_transcription",
]


from ._lib.router import router


class generate_image(router):
    pass

generate_image.init("xnano.resources.multimodal.resources", "generate_image")


class generate_audio(router):
    pass

generate_audio.init("xnano.resources.multimodal.resources", "generate_audio")


class generate_transcription(router):
    pass

generate_transcription.init("xnano.resources.multimodal.resources", "generate_transcription")

