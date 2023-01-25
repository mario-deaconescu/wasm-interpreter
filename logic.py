from __future__ import annotations

from dataclasses import dataclass

from custom_exceptions import EmptyOperandError
from evaluations import Evaluation, LocalGetter
from operations import ResultExpression
from variables import Stack, VariableWatch


class BlockExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        pass  # TODO: Implement this

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.assert_correctness(local_variables)


class LoopExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        pass  # TODO: Implement this

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.assert_correctness(local_variables)


class IfExpression(Evaluation):

    result: ResultExpression = None
    then_clause: Evaluation = None
    else_clause: Evaluation = None
    condition: Evaluation = None

    def __init__(self):
        super().__init__()
        if len(self.children) == 0:
            raise EmptyOperandError(1)
        if isinstance(self.children[0], ResultExpression):
            self.result = self.children[0]
            self.children = self.children[1:]
        if isinstance(self.children[0], LocalGetter):
            self.condition = self.children[0]
            self.children = self.children[1:]
        if not isinstance(self.children[0], ThenExpression):
            raise EmptyOperandError(1)
        self.then_clause = self.children[0]
        self.children = self.children[1:]
        if len(self.children) > 0:
            if not isinstance(self.children[0], ElseExpression):
                raise EmptyOperandError(1)
            self.else_clause = self.children[0]
            self.children = self.children[1:]

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.condition is not None:
            self.condition.evaluate(stack, local_variables)
        truth = stack.pop().value
        if truth == 1:
            self.then_clause.evaluate(stack, local_variables)
        else:
            self.else_clause.evaluate(stack, local_variables)

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> None:
        if self.condition is not None:
            self.condition.assert_correctness(local_variables)
        self.then_clause.assert_correctness(local_variables)
        if self.else_clause is not None:
            self.else_clause.assert_correctness(local_variables)


class ThenExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.assert_correctness(local_variables)


class ElseExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.assert_correctness(local_variables)


class SelectExpression(Evaluation):

    condition: Evaluation = None
    first_clause: Evaluation = None
    second_clause: Evaluation = None

    def __init__(self):
        super().__init__()
        if len(self.children) < 3:
            raise EmptyOperandError(3)
        self.condition, self.first_clause, self.second_clause = self.children
        self.children = []

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        self.condition.evaluate(stack, local_variables)
        truth = stack.pop().value
        if truth == 1:
            self.first_clause.evaluate(stack, local_variables)
        else:
            self.second_clause.evaluate(stack, local_variables)

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> None:
        for evaluation in [self.condition, self.first_clause, self.second_clause]:
            evaluation.assert_correctness(local_variables)
