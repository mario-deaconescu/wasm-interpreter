from __future__ import annotations

from dataclasses import dataclass

from custom_exceptions import EmptyOperandError
from evaluations import Evaluation, LocalGetter, EvaluationReport
from function import TypeExpression
from number_types import ResultExpression, ParamExpression
from variables import Stack, VariableWatch


class BlockExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport | None:
        for child in self.children:
            report: EvaluationReport | None = child.evaluate(stack, local_variables)
            if report is not None:
                if report.signal_break and (report.jump_to == 0 or report.jump_to == self.name):
                    break
                elif report.signal_break and isinstance(report.jump_to, int):
                    report.jump_to -= 1
                    return report
                if report.signal_return:
                    return report


class LoopExpression(Evaluation):

    def __init__(self, **kwargs):
        super().__init__()

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for child in self.children:
            child.evaluate(stack, local_variables)


class IfExpression(Evaluation):

    params: ParamExpression = None
    result: ResultExpression = None
    then_clause: Evaluation = None
    else_clause: Evaluation = None
    condition: Evaluation = None

    def __init__(self, **kwargs):
        super().__init__()
        Stack().contract(1)
        if len(self.children) == 0:
            EmptyOperandError.try_raise(1, Stack())
        if isinstance(self.children[0], ParamExpression):
            self.params = self.children[0]
            self.children = self.children[1:]
        if isinstance(self.children[0], TypeExpression):
            self.children = self.children[1:]
        if isinstance(self.children[0], ResultExpression):
            self.result = self.children[0]
            self.children = self.children[1:]
        if isinstance(self.children[0], Evaluation) and not isinstance(self.children[0], ThenExpression):
            self.condition = self.children[0]
            self.children = self.children[1:]
        if not isinstance(self.children[0], ThenExpression):
            EmptyOperandError.try_raise(1, Stack())
        self.then_clause = self.children[0]
        self.children = self.children[1:]
        if len(self.children) > 0:
            if not isinstance(self.children[0], ElseExpression):
                EmptyOperandError.try_raise(1, Stack())
            self.else_clause = self.children[0]
            self.children = self.children[1:]
        if self.result is not None:
            Stack().expand(len(self.result.number_types))
        if self.params is not None:
            Stack().contract(len(self.params.number_types))

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.condition is not None:
            self.condition.evaluate(stack, local_variables)
        truth = stack.pop().value
        if truth != 0:
            self.then_clause.evaluate(stack, local_variables)
        elif self.else_clause is not None:
            self.else_clause.evaluate(stack, local_variables)


class ThenExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)


class ElseExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)

class SelectExpression(Evaluation):

    condition: Evaluation = None
    first_clause: Evaluation = None
    second_clause: Evaluation = None

    def __init__(self, **kwargs):
        super().__init__()
        if len(self.children) < 3:
            EmptyOperandError.try_raise(3, Stack())
        self.first_clause, self.second_clause, self.condition = self.children
        self.children = []

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        self.condition.evaluate(stack, local_variables)
        truth = stack.pop().value
        if truth != 0:
            self.first_clause.evaluate(stack, local_variables)
        else:
            self.second_clause.evaluate(stack, local_variables)


class BranchExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport:
        for child in self.children[1:]:
            child.evaluate(stack, local_variables, global_variables)
        return EvaluationReport(signal_break=True, jump_to=self.children[0].expression_name)
