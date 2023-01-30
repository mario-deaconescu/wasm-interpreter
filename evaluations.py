from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Tuple

from custom_exceptions import InvalidNumberTypeError, UnknownVariableError, EmptyOperandError, UnexpectedTokenError, \
    UnreachableError
from enums import NumberType
from expressions import SExpression
from number_types import ResultExpression
from variables import FixedNumber, VariableWatch, Stack, GlobalVariableWatch, Memory


@dataclass
class EvaluationReport:
    jump_to: int | str | None = None
    signal_break: bool = False
    signal_return: bool = False


class Evaluation(SExpression):
    number_type: NumberType = None
    children: list[Evaluation]
    result: ResultExpression = None

    def __init__(self, **kwargs) -> None:
        super().__init__()
        if len(self.children) > 0 and isinstance(self.children[0], ResultExpression):
            self.result = self.children[0]
            self.children = self.children[1:]

    @abstractmethod
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if local_variables is None:
            local_variables = VariableWatch()
        if global_variables is None:
            global_variables = GlobalVariableWatch()

class UnaryEvaluation(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)

    @property
    def operand(self) -> Evaluation:
        if len(self.children) == 0:
            EmptyOperandError.try_raise(1, Stack())
            return Stack().pop()
        return self.children[0]

    def __init__(self, numeric=True, **kwargs) -> None:
        super().__init__()
        if len(self.children) < 1 and not kwargs.get('skip_operand_check', False):  # Special check for TypeExpression
            EmptyOperandError.try_raise(1, Stack())
        if numeric:
            if self.expression_name.startswith('v128') or self.expression_name.startswith('i16x8'):
                self.number_type = NumberType.v128
            else:
                self.number_type = NumberType(self.expression_name[:3])
            if isinstance(self.operand,
                          Evaluation) and self.operand.number_type is not None and self.operand.number_type != self.number_type:
                raise InvalidNumberTypeError(FixedNumber(None, self.operand.number_type), self.number_type)
        if len(self.children) == 1 and not kwargs.get('no_input', False):
            Stack().contract(1)
        Stack().expand(1)

    def check_and_evaluate(self, stack: Stack, local_variables: VariableWatch) -> FixedNumber:
        self.operand.evaluate(stack, local_variables)
        evaluation: FixedNumber = stack.pop()
        # if self.number_type is not None and not evaluation.number_type == self.number_type:
        #     raise InvalidNumberTypeError(evaluation, self.number_type)
        return evaluation


class BinaryEvaluation(Evaluation):

    @property
    def first_operand(self) -> Evaluation:
        if len(self.children) < 2:
            EmptyOperandError.try_raise(2, Stack())
            return Stack().pop()
        return self.children[0]

    @property
    def second_operand(self) -> Evaluation:
        if len(self.children) < 2:
            EmptyOperandError.try_raise(1, Stack())
            return Stack().pop()
        return self.children[1]

    def __init__(self, **kwargs) -> None:
        super().__init__()
        if len(self.children) < 2:
            EmptyOperandError.try_raise(2, Stack())
        self.number_type = NumberType(self.expression_name[:3])
        if isinstance(self.first_operand,
                      Evaluation) and self.first_operand.number_type is not None and self.first_operand.number_type != self.number_type:
            raise InvalidNumberTypeError(FixedNumber(None, self.first_operand.number_type), self.number_type)
        if isinstance(self.second_operand,
                      Evaluation) and self.second_operand.number_type is not None and self.second_operand.number_type != self.number_type:
            raise InvalidNumberTypeError(FixedNumber(None, self.second_operand.number_type), self.number_type)
        if len(self.children) == 2:
            Stack().contract(2)
        Stack().expand(1)

    def check_and_evaluate(self, stack: Stack, local_variables: VariableWatch = None,
                           global_variables: VariableWatch = None) -> tuple[FixedNumber, FixedNumber] | tuple[
        None, EvaluationReport]:
        if len(self.children) == 1:
            self.children[0].evaluate(stack, local_variables)
            second_evaluation: FixedNumber = stack.pop()
            first_evaluation: FixedNumber = stack.pop()
            return first_evaluation, second_evaluation
        first_operand = self.first_operand
        if isinstance(first_operand, Evaluation):
            report: EvaluationReport | None = first_operand.evaluate(stack, local_variables)
            if report is not None and report.signal_break:
                return None, report
            first_evaluation: FixedNumber = stack.pop()
        elif isinstance(first_operand, FixedNumber):
            first_evaluation: FixedNumber = first_operand
        second_operand = self.second_operand
        if isinstance(second_operand, Evaluation):
            report: EvaluationReport | None = second_operand.evaluate(stack, local_variables)
            if report is not None and report.signal_break:
                return None, report
            second_evaluation: FixedNumber = stack.pop()
        elif isinstance(second_operand, FixedNumber):
            second_evaluation: FixedNumber = second_operand
        if len(self.children) == 0:
            first_evaluation, second_evaluation = second_evaluation, first_evaluation
        if not first_evaluation.number_type == self.number_type:
            raise InvalidNumberTypeError(first_evaluation, self.number_type)
        if not second_evaluation.number_type == self.number_type:
            raise InvalidNumberTypeError(second_evaluation, self.number_type)
        return first_evaluation, second_evaluation

    @abstractmethod
    def evaluate(self, stack, local_variables: dict[str, FixedNumber] = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)


class LocalGetter(Evaluation):
    number_of_parameters: int = 1

    def __init__(self, **kwargs):
        super().__init__()
        self.number_of_parameters = 1
        Stack().expand(1)
        if self.name is None:
            if len(self.children) == 0:
                raise EmptyOperandError(1)
            try:
                self.name = int(self.children[0].expression_name)
            except ValueError:
                raise UnexpectedTokenError(self.children[0].expression_name)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.name not in local_variables:
            raise UnknownVariableError(self.name)
        stack.push(local_variables[self.name])


class LocalSetter(Evaluation):

    def __init__(self, **kwargs):
        super().__init__()
        if self.name is None:
            if len(self.children) == 0:
                raise EmptyOperandError(1)
            try:
                self.name = int(self.children[0].expression_name)
            except ValueError:
                raise UnexpectedTokenError(self.children[0].expression_name)
            self.children = self.children[1:]
        Stack().contract(1)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        self.children[0].evaluate(stack, local_variables)
        local_variables[self.name] = stack.pop()


class LocalExpression(Evaluation):
    number_type: NumberType = None
    variable_name: str = None

    def __init__(self, **kwargs):
        super().__init__()
        if '$' in self.expression_name:
            self.expression_name, self.variable_name, number_string = self.expression_name.split(" ")
        else:
            self.expression_name, number_string = self.expression_name.split(" ")
        self.number_type = NumberType(number_string)
        Stack().contract(1)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if local_variables is None:
            local_variables = VariableWatch()
        local_variables.add_variable(FixedNumber(0, self.number_type))


class LocalTee(LocalSetter):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Stack().expand(1)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        stack.push(local_variables[self.name])


class GlobalGetter(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if global_variables is None:
            global_variables = GlobalVariableWatch()
        if self.name not in global_variables:
            raise UnknownVariableError(self.name)
        stack.push(global_variables[self.name].value)


class GlobalSetter(UnaryEvaluation):

    def __init__(self, **kwargs):
        super().__init__(numeric=False)
        # Stack().contract(1)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if global_variables is None:
            global_variables = GlobalVariableWatch()
        if self.name not in global_variables:
            raise UnknownVariableError(self.name)
        if len(self.children) == 1:
            self.operand.evaluate(stack, local_variables)
            global_variables[self.name] = stack.pop()
        else:
            global_variables[self.name] = FixedNumber(0, self.number_type)


class LoadExpression(UnaryEvaluation):
    number_type: NumberType = None

    def __init__(self, **kwargs):
        super().__init__()

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if global_variables is None:
            global_variables = GlobalVariableWatch()
        self.operand.evaluate(stack, local_variables, global_variables)
        stack.push(Memory()[stack.pop().value, self.number_type])


class MemoryGrowExpression(UnaryEvaluation):
    number_type: NumberType = None

    def __init__(self, **kwargs):
        super().__init__(numeric=False)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        initial_size = Memory().allocated
        super().evaluate(stack, local_variables, global_variables)
        self.operand.evaluate(stack, local_variables, global_variables)
        Memory().grow(stack.pop().value)
        stack.push(FixedNumber(initial_size, NumberType.i32))


class StoreExpression(BinaryEvaluation):
    number_type: NumberType = None

    def __init__(self, **kwargs):
        super().__init__()
        Stack().contract(1)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables, global_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables, global_variables)
        Memory()[first_evaluation.value] = second_evaluation


class NOPExpression(Evaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        pass


class UnreachableExpression(Evaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        raise UnreachableError()


class GlobalExpression(Evaluation):
    mutable: bool = True
    number_type: NumberType = None
    variable_name: str = None
    number: Evaluation = None

    def __init__(self, variables=None):
        super().__init__()
        if '$' not in self.expression_name and self.name is None:
            raise InvalidNumberTypeError()
        if self.name is None:
            self.expression_name, self.variable_name = self.expression_name.split(" ")
        if self.children[0].expression_name == 'mut':
            self.mutable = True
            self.number_type = NumberType(self.children[0].children[0].expression_name)
            self.children = self.children[1:]
        self.number = self.children[0]
        self.evaluate(Stack(), variables, global_variables=GlobalVariableWatch())
        Stack().contract(1)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if local_variables is None:
            local_variables = VariableWatch()
        self.number.evaluate(stack, local_variables, global_variables)
        index = stack.pop().value
        global_variables.add_variable(FixedNumber(index, self.number_type), self.mutable, self.name)
