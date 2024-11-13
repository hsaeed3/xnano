# generation process mode for basemodel.model_generate()
#   or basemodel.model_async_generate()


from typing import Literal


# process
BaseModelGenerationProcess = Literal["batch", "sequential"]
