from xnano.pydantic import BaseModel

class Test(BaseModel):
    a: int
    b: str

print(Test(a=1, b="2"))

print(Test.model_completion("what is this?"))