from evaluations import Evaluation
from variables import Stack, VariableWatch


class DropExpression(Evaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for child in self.children:
            child.evaluate(stack, local_variables)
        stack.pop()
