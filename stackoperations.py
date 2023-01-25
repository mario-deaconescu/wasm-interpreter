from evaluations import Evaluation
from variables import Stack, VariableWatch


class DropExpression(Evaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        stack.pop()
