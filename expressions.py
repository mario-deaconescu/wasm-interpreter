from __future__ import annotations

import re
import sys
from abc import abstractmethod
from dataclasses import dataclass
from re import Match, Pattern
from typing import Any, Type

from custom_exceptions import InvalidNumberTypeError, UnknownVariableError, InvalidSyntaxError, UnknownFunctionError, \
    InvalidFunctionSignatureError, WebAssemblyException, EXCEPTION_NAMES
from enums import NumberType
from functions import FixedNumber

EXPORTED_FUNCTIONS: dict[str, FunctionExpression] = {}

CLASSES_DICT: dict[str, str] = {
    'module': 'Module',
    'func': 'FunctionExpression',
    'export': 'ExportExpression',
    'param': 'ParamExpression',
    'result': 'ResultExpression',
    'local.get': 'LocalGetter',
    'assert_return': 'AssertReturnExpression',
    'assert_invalid': 'AssertInvalidExpression',
    'add': 'AddExpression',
    'const': 'ConstExpression',
}


@dataclass
class NumberVariable:
    number_type: NumberType
    name: str | None


class SExpression:
    expression_name: str
    name: str = None
    children: list[SExpression] = []

    @staticmethod
    def get_parentheses(expression: str) -> list[str]:
        if len(expression) == 0:
            return []
        parentheses: list[str] = []
        index: int = 0
        open_parentheses: int = 0
        parenthesis_regex: Pattern[str] = re.compile('[()]')
        current_parenthesis: str = ""
        while index < len(expression):
            next_parenthesis = parenthesis_regex.search(expression, index)
            if next_parenthesis is None:
                if open_parentheses != 0:
                    # Expression is invalid
                    raise InvalidSyntaxError(f'Expression "{expression}" has invalid parentheses')
                break

            if expression[next_parenthesis.start()] == ')':
                open_parentheses -= 1
                if open_parentheses < 0:
                    raise InvalidSyntaxError(f'Expression "{expression}" has invalid parentheses')
                current_parenthesis += expression[index:next_parenthesis.end()]
            else:
                open_parentheses += 1
                if open_parentheses == 1:
                    # This is the first parenthesis in this set
                    current_parenthesis += '('
                else:
                    current_parenthesis += expression[index:next_parenthesis.end()]

            if open_parentheses == 0:
                # We found a valid parentheses set
                parentheses.append(current_parenthesis)
                current_parenthesis = ""

            index = next_parenthesis.end()

        if len(parentheses) > 0:
            # We might still have an operator
            remaining_expression = expression[index + 1:]
            if remaining_expression:
                parentheses.append(remaining_expression.strip(' '))

            # We found our parentheses
            return parentheses

        # Check if there is a variable name
        if expression[0] == '$':
            return expression.split(' ', 1)

        return [expression]

    def assert_correctness(self, local_variables: dict[str | int, NumberVariable]):
        for child in self.children:
            child.assert_correctness(local_variables)

    def __new__(cls, expression_string: str) -> SExpression:
        instance = super().__new__(cls)

        # Check if expression has surrounding parentheses
        parentheses_match: Match[str] | None = re.fullmatch(r'\(.*\)', expression_string)
        if parentheses_match is None:
            # No surrounding parentheses
            instance.expression_name = expression_string
            return instance

        # Remove redundant parentheses
        expression_string = expression_string[1:-1].strip()

        # Separate name from children
        children_string: str = ""

        # Special case for "invoke"
        if expression_string.startswith('invoke'):
            triple_expression: list[str] = expression_string.split(' ', 2)
            split_expression: tuple[str, ...] = (f'{triple_expression[0]} {triple_expression[1]}', triple_expression[2])
            instance.__class__ = InvokeExpression
        else:
            split_expression: tuple[str, ...] = tuple(expression_string.split(' ', 1))
        instance.expression_name = split_expression[0]
        if len(split_expression) > 1:
            children_string = split_expression[1]

        c = []
        for x in SExpression.get_parentheses(children_string):
            c.append(SExpression(x))
        instance.children = c

        # Check if expression has a name
        if len(instance.children) > 0 and instance.children[0].expression_name[0] == '$':
            # The name is the variable name without the '$'
            instance.name = instance.children[0].expression_name[1:]
            # Remove the variable name from the children
            instance.children = instance.children[1:]

        # Check if it's a predefined function
        new_type: str = instance.expression_name
        if re.fullmatch(r'.{3}\.([a-z_]+)', instance.expression_name) is not None:
            new_type = new_type[4:]

        # Check expression type
        if new_type in CLASSES_DICT.keys():
            instance.__class__ = getattr(sys.modules[__name__], CLASSES_DICT[new_type])

        return instance

    def __init__(self, _=None) -> None:
        pass

    def __str__(self) -> str:
        return f'{self.expression_name}' + (
            f'({self.name})' if self.name is not None else '')

    def __repr__(self, level=0) -> str:
        return '\t' * level + '- ' + str(self) + '\n' + ''.join([child.__repr__(level + 1) for child in self.children])


class Module(SExpression):
    pass


class Evaluation(SExpression):
    number_type: NumberType = None
    children: list[Evaluation]

    @abstractmethod
    def evaluate(self, local_variables: dict[str, FixedNumber]) -> FixedNumber:
        pass

    def assert_correctness(self, local_variables: dict[str | int, NumberVariable]) -> NumberType:
        return self.number_type


class FunctionExpression(Evaluation):
    export_as: str = None
    parameters: list[NumberVariable]
    result_type: NumberType | None = None

    def __str__(self) -> str:
        representation: str = super().__str__()
        parameter_representations: list[str] = []
        for parameter in self.parameters:
            if parameter.name is None:
                parameter_representations.append(parameter.number_type.value)
            else:
                parameter_representations.append(f"{parameter.name}: {str(parameter.number_type.value)}")
        representation += f"({', '.join(parameter_representations)})"
        representation += f" -> {self.result_type.value if self.result_type is not None else 'None'}"
        representation += f' (exported as "{self.export_as}")'
        return representation

    def __init__(self, _=None) -> None:
        super().__init__()
        self.parameters = []
        if len(self.children) > 0:
            if isinstance(self.children[0], ExportExpression):
                export_expression: ExportExpression = self.children[0]
                self.export_as = export_expression.export_name
                self.children = self.children[1:]
                EXPORTED_FUNCTIONS[self.export_as] = self
        child_index: int = 0
        while child_index < len(self.children) and isinstance(self.children[child_index], ParamExpression):
            parameter_expression: ParamExpression = self.children[child_index]
            self.parameters.append(NumberVariable(parameter_expression.number_type, parameter_expression.name))
            child_index += 1
        # Remove parameters from children
        self.children = self.children[child_index:]
        if len(self.children) > 0:
            if isinstance(self.children[0], ResultExpression):
                result_expression: ResultExpression = self.children[0]
                self.result_type = result_expression.number_type
                self.children = self.children[1:]

    def initialize_parameters(self, local_variables: dict[str | int, NumberVariable] | dict[str | int, FixedNumber],
                              *args: NumberVariable | FixedNumber) \
            -> dict[str | int, NumberVariable] | dict[str | int, FixedNumber]:
        # Check parameters
        if len(args) != len(self.parameters):
            raise InvalidFunctionSignatureError(self, *args)
        for index, arg in enumerate(args):
            if self.parameters[index].number_type != arg.number_type:
                raise TypeError("Invalid parameter type")
            # Variables are referenced by number
            local_variables[index] = arg
            # Variables can also be referenced by name
            if self.parameters[index].name is not None:
                local_variables[self.parameters[index].name] = arg
        for expression in self.children:
            if not isinstance(expression, Evaluation):
                raise TypeError("Expression can not be evaluated")
        return local_variables

    def assert_correctness(self, local_variables: dict[str | int, NumberVariable], *args: NumberVariable) -> NumberType:
        # Check parameters
        local_variables = self.initialize_parameters(local_variables, *args)
        if len(self.children) == 1:
            evaluation: Evaluation = self.children[0]
            return evaluation.assert_correctness(local_variables)

    def evaluate(self, local_variables: dict[str | int, FixedNumber], *args: FixedNumber) -> FixedNumber:
        # Check parameters
        local_variables = self.initialize_parameters(local_variables, *args)
        if len(self.children) == 1:
            evaluation: Evaluation = self.children[0]
            return evaluation.evaluate(local_variables)


class ExportExpression(SExpression):
    export_name: str

    def __init__(self, _=None) -> None:
        super().__init__()
        if len(self.children) != 1:
            raise InvalidSyntaxError(f"Export expression has incorrect number of parameters ({len(self.children)})")
        # Remove "" from name
        self.export_name = self.children[0].expression_name[1:-1]
        self.children = []


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


class ParamExpression(NumberTypeExpression):
    pass


class ResultExpression(NumberTypeExpression):
    pass


class UnaryEvaluation(Evaluation):

    @property
    def operand(self) -> Evaluation:
        return self.children[0]

    def __init__(self, _=None) -> None:
        super().__init__()
        self.number_type = NumberType(self.expression_name[:3])

    def assert_correctness(self, local_variables: dict[str | int, NumberVariable]) -> NumberType:
        return_type: NumberType = self.operand.assert_correctness(local_variables)
        if not return_type == self.number_type:
            raise InvalidNumberTypeError(FixedNumber(0, return_type), self.number_type)
        return self.number_type

    def check_and_evaluate(self, local_variables: dict[str | int, FixedNumber]) -> FixedNumber:
        evaluation: FixedNumber = self.operand.evaluate(local_variables)
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

    def assert_correctness(self, local_variables: dict[str | int, NumberVariable]) -> NumberType:
        return_type1: NumberType = self.first_operand.assert_correctness(local_variables)
        return_type2: NumberType = self.second_operand.assert_correctness(local_variables)
        if not return_type1 == self.number_type:
            raise InvalidNumberTypeError(FixedNumber(0, return_type1), self.number_type)
        if not return_type2 == self.number_type:
            raise InvalidNumberTypeError(FixedNumber(0, return_type2), self.number_type)
        return self.number_type

    def check_and_evaluate(self, local_variables: dict[str | int, FixedNumber]) -> tuple[FixedNumber, FixedNumber]:
        first_evaluation: FixedNumber = self.first_operand.evaluate(local_variables)
        second_evaluation: FixedNumber = self.second_operand.evaluate(local_variables)
        if not first_evaluation.number_type == self.number_type:
            raise InvalidNumberTypeError(first_evaluation, self.number_type)
        if not second_evaluation.number_type == self.number_type:
            raise InvalidNumberTypeError(second_evaluation, self.number_type)
        return first_evaluation, second_evaluation

    @abstractmethod
    def evaluate(self, local_variables: dict[str, FixedNumber]) -> FixedNumber:
        pass


class AddExpression(BinaryEvaluation):

    def evaluate(self, local_variables: dict[str | int, FixedNumber]) -> FixedNumber:
        first_evaluation, second_evaluation = self.check_and_evaluate(local_variables)
        return FixedNumber(first_evaluation.value + second_evaluation.value, self.number_type)

    def __init__(self, _=None) -> None:
        super().__init__()
        if len(self.children) != 2:
            raise ValueError(f"Invalid number of operand for add operation ({len(self.children)})")


class LocalGetter(Evaluation):

    def evaluate(self, local_variables: dict[str | int, FixedNumber]) -> FixedNumber:
        if self.name not in local_variables:
            raise UnknownVariableError(self.name)
        return local_variables[self.name]


class ConstExpression(UnaryEvaluation):
    value: FixedNumber

    def __init__(self, _=None) -> None:
        super().__init__()
        value: int | float
        # Try to cast number to int
        try:
            value = int(self.operand.expression_name)
        except ValueError:
            value = float(self.operand.expression_name)
        if self.number_type == NumberType.f32:
            value = float(value)
        self.value = FixedNumber(value, self.number_type)

    def assert_correctness(self, local_variables: dict[str | int, NumberVariable]) -> NumberType:
        return self.number_type

    def evaluate(self, local_variables: dict[str | int, FixedNumber]) -> FixedNumber:
        return self.value


class InvokeExpression(Evaluation):
    function: FunctionExpression = None

    def __init__(self, _=None) -> None:
        super().__init__(self)
        self.expression_name, function_name = self.expression_name.split(' ')
        function_name = function_name.strip('"')
        if function_name not in EXPORTED_FUNCTIONS:
            raise UnknownFunctionError(function_name)

        self.function = EXPORTED_FUNCTIONS[function_name]

    def evaluate(self, local_variables: dict[str | int, FixedNumber]) -> FixedNumber:
        parameters: list[FixedNumber] = [evaluation.evaluate(local_variables) for evaluation in self.children]
        return self.function.evaluate(local_variables, *parameters)

    def __str__(self):
        return f'{super().__str__()}({self.function.export_as})'


class AssertExpression(SExpression):

    @property
    def assert_operand(self) -> SExpression:
        return self.children[0]

    @property
    def assert_return(self) -> SExpression:
        return self.children[1]

    @abstractmethod
    def assert_expression(self) -> bool:
        pass


class AssertInvalidExpression(AssertExpression):

    def assert_expression(self) -> bool:
        if not isinstance(self.assert_operand, Module):
            raise TypeError(
                f"Invalid assert operand: Expected Module, got {self.assert_operand.__class__.__name__}")

        # Check if return type is string
        string_regex: Pattern[str] = re.compile('"([a-zA-Z ]+)"')
        if not string_regex.fullmatch(self.assert_return.expression_name):
            raise TypeError(
                f"Invalid assert result: Expected string, got {self.assert_operand.expression_name}")

        exception_name: str = self.assert_return.expression_name.strip('"')  # Remove " " from name

        try:
            self.assert_operand.assert_correctness({})
        except WebAssemblyException as exception:
            # Check if it's the right exception
            expected_exception: Type = getattr(sys.modules[__name__], EXCEPTION_NAMES[exception_name])
            return isinstance(exception, expected_exception)

        return False


class AssertReturnExpression(AssertExpression):

    def assert_expression(self) -> bool:
        if not isinstance(self.assert_operand, Evaluation):
            raise TypeError(
                f"Invalid assert operand: Expected Evaluation, got {self.assert_operand.__class__.__name__}")
        if not isinstance(self.assert_return, Evaluation):
            raise TypeError(f"Invalid assert result: Expected Evaluation, got {self.assert_return.__class__.__name__}")
        evaluation: Evaluation = self.assert_operand
        result: FixedNumber = evaluation.evaluate({})

        expected_evaluation: Evaluation = self.assert_return
        expected_result: FixedNumber = expected_evaluation.evaluate({})

        return result == expected_result
