from evaluations import Evaluation
from variables import Stack, VariableWatch


class DropExpression(Evaluation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Stack().contract(1)
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for child in self.children:
            child.evaluate(stack, local_variables)
        stack.pop()
