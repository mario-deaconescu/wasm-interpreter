from __future__ import annotations

from custom_exceptions import InvalidSyntaxError, DivisionByZeroError
from enums import NumberType

from evaluations import BinaryEvaluation, UnaryEvaluation
from expressions import SExpression
from variables import VariableWatch, FixedNumber, Stack


class NumberTypeExpression(SExpression):
    number_type: NumberType

    def __init__(self, _=None) -> None:
        super().__init__()
        if len(self.children) != 1:
            raise InvalidSyntaxError(f"Number expression has incorrect number of parameters ({len(self.children)})")
        match self.children[0].expression_name:
            case 'i32':
                self.number_type = NumberType.i32
            case 'i64':
                self.number_type = NumberType.i64
            case 'f32':
                self.number_type = NumberType.f32
            case 'f64':
                self.number_type = NumberType.f64
            case _:
                raise ValueError("Invalid number type")
        self.children = []


class ResultExpression(NumberTypeExpression):
    pass


class ParamExpression(NumberTypeExpression):
    pass


class EqzExpression(UnaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        evaluation: FixedNumber = self.check_and_evaluate(stack, local_variables)
        if evaluation.value == 0:
            stack.push(FixedNumber(1, self.number_type))
        else:
            stack.push(FixedNumber(0, self.number_type))


class ConstExpression(UnaryEvaluation):
    value: FixedNumber

    def __init__(self, _=None) -> None:
        super().__init__()
        value: int | float
        if self.number_type == NumberType.i32 or self.number_type == NumberType.i64:
            value = int(self.operand.expression_name, 0)
        else:
            value = float(self.operand.expression_name)
        self.value = FixedNumber(value, self.number_type)

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> NumberType:
        return self.number_type

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        stack.push(self.value)


class AddExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(first_evaluation.value + second_evaluation.value, self.number_type))


class SubExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(first_evaluation.value - second_evaluation.value, self.number_type))


class MulExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(first_evaluation.value * second_evaluation.value, self.number_type))

class DivSignedExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        if second_evaluation.value == 0:
            raise DivisionByZeroError()
        stack.push(FixedNumber(first_evaluation.value // second_evaluation.value, self.number_type))

class DivUnsignedExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables = None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluatation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(((first_evaluation & 0xffffffffffffffff)//(second_evaluatation & 0xffffffffffffffff))&0xffffffffffffffff, self.number_type))
        # TODO cazul in care seecond_evaluation este 0

class AndExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables = None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(first_evaluation & second_evaluation, self.number_type))





