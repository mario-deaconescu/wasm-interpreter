from __future__ import annotations
from typing import TYPE_CHECKING

from enums import NumberType

if TYPE_CHECKING:
    from function import FunctionExpression
    from variables import FixedNumber, NumberVariable, Stack

EXCEPTION_NAMES: dict[str, list[str]] = {
    'type mismatch': ['InvalidNumberTypeError', 'EmptyOperandError', 'InvalidFunctionResultError'],
    'integer divide by zero': ['DivisionByZeroError'],
    'integer overflow': ['IntegerOverflowError'],
    'unexpected token': ['UnexpectedTokenError'],
    'undefined element': ['UndefinedElementError'],
    'inline function type': ['UnexpectedTokenError'],
    'mismatching label': ['UnexpectedTokenError'],
    'unknown label': ['UnknownLabelError'],
}


class WebAssemblyException(Exception):
    pass


class InvalidNumberTypeError(WebAssemblyException):

    def __init__(self, number: FixedNumber = None, expected_number_type: NumberType = None):
        if number is None and expected_number_type is None:
            super().__init__('Invalid number type')
            return
        self.number = number
        self.expected_number_type = expected_number_type
        message: str = f'Invalid number type: Expected number type "{expected_number_type.name}" and got ' \
                       f'"{number.number_type.name if number.number_type.name is not None else number.value}" '
        super().__init__(message)


class UnknownVariableError(WebAssemblyException):

    def __init__(self, variable_name: str):
        self.variable_name = variable_name
        message: str = f'Variable "{variable_name}" not found'
        super().__init__(message)


class UnknownFunctionError(WebAssemblyException):

    def __init__(self, function_name: str):
        self.function_name = function_name
        message: str = f'Function "{function_name}" not found'
        super().__init__(message)


class InvalidSyntaxError(WebAssemblyException):
    pass


class InvalidFunctionSignatureError(WebAssemblyException):

    def __init__(self, function: FunctionExpression, *args: FixedNumber | NumberVariable):
        self.function = function
        self.parameters = args
        message: str = f'Function "{function.name}" expected {len(function.parameters)} and got {len(args)}'
        super().__init__(message)


class InvalidFunctionResultError(WebAssemblyException):

        def __init__(self, function: FunctionExpression, *results: FixedNumber | NumberVariable):
            self.function = function
            self.result = results
            message: str = f'Function "{function.name}" expected {len(function.result_types) if function.result_types else 0} and got {len(results)}'
            super().__init__(message)


class StackOverflowError(WebAssemblyException):

    def __init__(self, stack_size: int):
        self.stack_size = stack_size
        message: str = f'Stack overflow: Stack size is {stack_size}'
        super().__init__(message)


class StackEmptyError(WebAssemblyException):

    def __init__(self):
        message: str = 'Stack is empty'
        super().__init__(message)


class EmptyOperandError(WebAssemblyException):

    @staticmethod
    def try_raise(expected_operands: int, stack: Stack | None = None):
        if stack is None:
            raise EmptyOperandError(expected_operands)
        if len(stack) < expected_operands:
            raise EmptyOperandError(expected_operands)
        
    def __init__(self, expected_operands: int):
        self.expected_operands = expected_operands
        message: str = f'Expected {expected_operands} operands'
        super().__init__(message)


class DivisionByZeroError(WebAssemblyException):

    def __init__(self):
        message: str = 'Division by zero'
        super().__init__(message)


class IntegerOverflowError(WebAssemblyException):

    def __init__(self):
        message: str = f'Integer overflow: value is too large'
        super().__init__(message)


class UnexpectedTokenError(WebAssemblyException):

    def __init__(self, token: str):
        self.token = token
        message: str = f'Unexpected token: "{token}"'
        super().__init__(message)


class UndefinedElementError(WebAssemblyException):

        def __init__(self, message: str = 'Undefined Element!'):
            super().__init__(message)


class UnreachableError(WebAssemblyException):

    def __init__(self):
        message: str = 'Unreachable code'
        super().__init__(message)


class UnknownLabelError(WebAssemblyException):

    def __init__(self, label: str):
        self.label = label
        message: str = f'Unknown label: "{label}"'
        super().__init__(message)