from __future__ import annotations

from dataclasses import dataclass

from custom_exceptions import EmptyOperandError, InvalidNumberTypeError, UnknownLabelError
from enums import NumberType
from evaluations import Evaluation, LocalGetter, EvaluationReport
from expressions import SExpression
from function import TypeExpression
from number_types import ResultExpression, ParamExpression
from operations import ConstExpression
from variables import Stack, VariableWatch


class BlockExpression(Evaluation):

    def __init__(self, variables=None, **kwargs):
        super().__init__(**kwargs)
        if self.result is not None:
            Stack().size_to(len(self.result.number_types))
        else:
            Stack().size_to(0)
        variables['~blocks~'] += 1

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport | None:
        for child in self.children:
            report: EvaluationReport | None = child.evaluate(stack, local_variables)
            if report is not None:
                if report.jump_to is not None:
                    try:
                        report.jump_to = int(report.jump_to)
                    except ValueError:
                        pass
                if report.signal_break and (report.jump_to == 0 or report.jump_to == '$' + self.name):
                    break
                elif report.signal_break and isinstance(report.jump_to, int):
                    report.jump_to -= 1
                    return report
                if report.signal_return or report.signal_break:
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

    then_results: int = None
    else_results: int = None

    def __init__(self, variables=None):
        super().__init__()
        number_of_params = 0
        results: list[NumberType] = []
        if len(self.children) == 0:
            EmptyOperandError.try_raise(1, Stack())
        if isinstance(self.children[0], ParamExpression):
            self.params = self.children[0]
            self.children = self.children[1:]
            number_of_params = len(self.params.number_types)
        if isinstance(self.children[0], TypeExpression):
            type_expression: TypeExpression = self.children[0]
            number_of_params = len(type_expression.parameters)
            if type_expression.results is not None:
                results = type_expression.results
            if len(type_expression.parameters) != len(Stack()):
                raise InvalidNumberTypeError()
            self.children = self.children[1:]
            # TODO check if the types are correct
            while isinstance(self.children[0], ParamExpression):
                self.children = self.children[1:]
            while isinstance(self.children[0], ResultExpression):
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
            results = self.result.number_types
        # if self.condition is None:
        #     Stack().contract(1)
        # if self.result is not None:
        #     Stack().expand(len(self.result.number_types))
        # elif results:
        #     Stack().expand(len(results))
        # if self.params is not None:
        #     Stack().contract(len(self.params.number_types))
        if variables['~assert~'] and self.then_results is not None and self.then_results != len(results):
            raise InvalidNumberTypeError(None, None)
        if variables['~assert~'] and self.else_results is not None and self.else_results != len(results):
            raise InvalidNumberTypeError(None, None)
        if variables['~assert~'] and self.result is not None and (self.else_results == 0 or self.else_results is None):
            raise InvalidNumberTypeError(None, None)
        if self.result is not None:
            if len(self.then_clause.children) > 0 and isinstance(self.then_clause.children[0], ConstExpression):
                const: ConstExpression = self.then_clause.children[0]
                if const.number_type != self.result.number_types[0]:
                    raise InvalidNumberTypeError(None, None)
            if self.else_clause is not None and len(self.else_clause.children) > 0 and isinstance(self.else_clause.children[0], ConstExpression):
                const: ConstExpression = self.else_clause.children[0]
                if const.number_type != self.result.number_types[0]:
                    raise InvalidNumberTypeError(None, None)
        if self.result is not None:
            Stack().size_to(len(self.result.number_types))
        elif results:
            Stack().size_to(len(results))
        else:
            Stack().size_to(0)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.condition is not None:
            self.condition.evaluate(stack, local_variables, global_variables)
        truth = stack.pop().value
        if truth != 0:
            self.then_clause.evaluate(stack, local_variables)
        elif self.else_clause is not None:
            self.else_clause.evaluate(stack, local_variables)


class ThenExpression(Evaluation):
    result_size = 0


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_size = len(Stack())

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for evaluation in self.children:
            report: EvaluationReport | None = evaluation.evaluate(stack, local_variables, global_variables)
            if report is not None:
                if report.jump_to is not None:
                    try:
                        report.jump_to = int(report.jump_to)
                    except ValueError:
                        pass
                if report.signal_break and (report.jump_to == 0 or report.jump_to == self.name):
                    break
                elif report.signal_break and isinstance(report.jump_to, int):
                    report.jump_to -= 1
                    return report
                if report.signal_return:
                    return report



class ElseExpression(Evaluation):
    result_size = 0


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_size = len(Stack())

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        for evaluation in self.children:
            report: EvaluationReport | None = evaluation.evaluate(stack, local_variables, global_variables)
            if report is not None:
                if report.jump_to is not None:
                    try:
                        report.jump_to = int(report.jump_to)
                    except ValueError:
                        pass
                if report.signal_break and (report.jump_to == 0 or report.jump_to == self.name):
                    break
                elif report.signal_break and isinstance(report.jump_to, int):
                    report.jump_to -= 1
                    return report
                if report.signal_return:
                    return report

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
        Stack().contract(2)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        self.condition.evaluate(stack, local_variables)
        truth = stack.pop().value
        if truth != 0:
            self.first_clause.evaluate(stack, local_variables)
        else:
            self.second_clause.evaluate(stack, local_variables)


class BranchExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport:
        for child in self.children:
            child.evaluate(stack, local_variables, global_variables)
        if self.name is not None:
            return EvaluationReport(signal_break=True, jump_to=self.name)
        return EvaluationReport(signal_break=True, jump_to=self.children[0].expression_name)


class BranchIfExpression(Evaluation):

    def __init__(self, **kwargs):
        super().__init__()
        if len(self.children) < 2:
            EmptyOperandError.try_raise(2, Stack())

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport:
        self.children[-1].evaluate(stack, local_variables, global_variables)
        truth = stack.pop().value
        if truth != 0:
            self.children[1].evaluate(stack, local_variables, global_variables)
            return EvaluationReport(signal_break=True, jump_to=self.children[0].expression_name)


class BranchTableExpression(Evaluation):

    def __init__(self, variables=None, **kwargs):
        super().__init__(**kwargs)
        if self.children[0].__class__ == SExpression:
            if len(self.children) == 1 and len(self.children[0].expression_name.split(' ')) < 2:
                EmptyOperandError.try_raise(2, Stack())
            else:
                try:
                    index = int(self.children[0].expression_name)
                except ValueError:
                    pass
                else:
                    if index < 0 or index >= variables['~blocks~']:
                        raise UnknownLabelError(str(index))
            return
        Stack().contract(1)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport:
        for child in [child for child in self.children if isinstance(child, Evaluation)]:
            child.evaluate(stack, local_variables, global_variables)
        value = stack.pop().value
        index = 0
        if self.name is not None:
            table = self.name.strip(' ').split(' ')
        else:
            table = self.children[0].expression_name.split(' ')
        for element in table[:-1]:
            if index == value:
                return EvaluationReport(signal_break=True, jump_to=element)
            index += 1
        return EvaluationReport(signal_break=True, jump_to=table[-1])