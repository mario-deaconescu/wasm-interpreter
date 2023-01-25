from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass

from custom_exceptions import InvalidNumberTypeError, UnknownVariableError, EmptyOperandError
from enums import NumberType
from expressions import SExpression
from variables import FixedNumber, VariableWatch, Stack, GlobalVariableWatch


@dataclass
class EvaluationReport:
    jump_to: int | str | None = None
    signal_break: bool = False
    signal_return: bool = False


class Evaluation(SExpression):
    number_type: NumberType = None
    children: list[Evaluation]

    @abstractmethod
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if local_variables is None:
            local_variables = VariableWatch()
        if global_variables is None:
            global_variables = GlobalVariableWatch()

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> NumberType:
        return self.number_type


class UnaryEvaluation(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)

    @property
    def operand(self) -> Evaluation:
        if len(self.children) == 0:
            raise EmptyOperandError(1)
        return self.children[0]

    def __init__(self, numeric=True) -> None:
        super().__init__()
        if numeric:
            self.number_type = NumberType(self.expression_name[:3])

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> NumberType:
        return_type: NumberType = self.operand.assert_correctness(local_variables)
        if not return_type == self.number_type:
            raise InvalidNumberTypeError(FixedNumber(0, return_type), self.number_type)
        return self.number_type

    def check_and_evaluate(self, stack: Stack, local_variables: VariableWatch) -> FixedNumber:
        self.operand.evaluate(stack, local_variables)
        evaluation: FixedNumber = stack.pop()
        if not evaluation.number_type == self.number_type:
            raise InvalidNumberTypeError(evaluation, self.number_type)
        return evaluation


class BinaryEvaluation(Evaluation):

    @property
    def first_operand(self) -> Evaluation:
        return self.children[0]

    @property
    def second_operand(self) -> Evaluation:
        return self.children[1]

    def __init__(self, _=None) -> None:
        super().__init__()
        self.number_type = NumberType(self.expression_name[:3])
        if len(self.children) != 2:
            raise ValueError(f"Invalid number of operand for add operation ({len(self.children)})")

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> NumberType:
        return_type1: NumberType = self.first_operand.assert_correctness(local_variables)
        return_type2: NumberType = self.second_operand.assert_correctness(local_variables)
        if not return_type1 == self.number_type:
            raise InvalidNumberTypeError(FixedNumber(0, return_type1), self.number_type)
        if not return_type2 == self.number_type:
            raise InvalidNumberTypeError(FixedNumber(0, return_type2), self.number_type)
        return self.number_type

    def check_and_evaluate(self, stack: Stack, local_variables: VariableWatch = None) -> tuple[
        FixedNumber, FixedNumber]:
        self.first_operand.evaluate(stack, local_variables)
        first_evaluation: FixedNumber = stack.pop()
        self.second_operand.evaluate(stack, local_variables)
        second_evaluation: FixedNumber = stack.pop()
        if not first_evaluation.number_type == self.number_type:
            raise InvalidNumberTypeError(first_evaluation, self.number_type)
        if not second_evaluation.number_type == self.number_type:
            raise InvalidNumberTypeError(second_evaluation, self.number_type)
        return first_evaluation, second_evaluation

    @abstractmethod
    def evaluate(self, stack, local_variables: dict[str, FixedNumber] = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)


class LocalGetter(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.name not in local_variables:
            raise UnknownVariableError(self.name)
        stack.push(local_variables[self.name])


class LocalSetter(UnaryEvaluation):

    def __init__(self):
        super().__init__(numeric=False)
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.name not in local_variables:
            raise UnknownVariableError(self.name)
        self.operand.evaluate(stack, local_variables)
        local_variables[self.name] = stack.pop()

class LocalExpression(Evaluation):
    number_type: NumberType = None

    def __init__(self):
        self.expression_name, number_string = self.expression_name.split(" ")
        self.number_type = NumberType(number_string)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if local_variables is None:
            local_variables = VariableWatch()
        local_variables.add_variable(FixedNumber(0, self.number_type))


class LocalTee(LocalSetter):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        stack.push(local_variables[self.name])


class GlobalGetter(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.name not in global_variables:
            raise UnknownVariableError(self.name)
        stack.push(global_variables[self.name])


class GlobalSetter(UnaryEvaluation):

    def __init__(self):
        super().__init__(numeric=False)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if self.name not in global_variables:
            raise UnknownVariableError(self.name)
        if len(self.children) == 1:
            self.operand.evaluate(stack, local_variables)
            global_variables[self.name] = stack.pop()
        else:
            global_variables[self.name] = FixedNumber(0, self.number_type)


class LoadExpression(UnaryEvaluation):
    number_type: NumberType = None

    def __init__(self):
        super().__init__()

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        if global_variables is None:
            global_variables = VariableWatch()
        self.operand.evaluate(stack, local_variables, global_variables)