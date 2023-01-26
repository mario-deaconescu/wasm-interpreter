from __future__ import annotations

import ctypes
import math

from dataclasses import dataclass
from typing import Any

from custom_exceptions import StackEmptyError, StackOverflowError, InvalidNumberTypeError
from enums import NumberType
from singleton import singleton


@dataclass
class NumberVariable:
    number_type: NumberType
    name: str | None


class VariableWatch:
    _variable_counter: int = 0
    _variables: dict[int | str, Any] = {}

    def __init__(self):
        self._variable_counter = 0
        self._variables = {}

    def __getitem__(self, item):
        if isinstance(item, str) and not item.startswith('$'):
            item = '$' + item
        return self._variables[item]

    def add_variable(self, value, name=None) -> None:
        self._variables[self._variable_counter] = value
        self._variable_counter += 1
        if name is not None:
            if not name.startswith('$'):
                name = '$' + name
            self._variables[name] = value

    def __setitem__(self, key: str | int, value):
        if isinstance(key, int):
            self._variables[key] = value
        else:
            self._variables['$' + key] = value

    def __contains__(self, item: str | int) -> bool:
        if isinstance(item, str) and not item.startswith('$'):
            item = '$' + item
        return item in self._variables


@singleton
class Stack:
    _stack: list[Any] = []

    def __init__(self, stack_size: int = 1024):
        self._stack = []
        self._stack_size = stack_size

    def pop(self) -> Any:
        if len(self._stack) == 0:
            raise StackEmptyError()
        return self._stack.pop()

    def push(self, value: Any) -> None:
        if len(self._stack) == self._stack_size:
            raise StackOverflowError(self._stack_size)
        self._stack.append(value)

    def __getitem__(self, item: int) -> Any:
        return self._stack[-item - 1]

    def __del__(self):
        self._stack = []


@dataclass
class FixedNumber:
    _value: int | float
    number_type: NumberType

    def __post_init__(self) -> None:
        self._value = assert_number_type(self._value, self.number_type)

    @property
    def value(self) -> int | float:
        return self._value

    @value.setter
    def value(self, new_value: int | float):
        self._value = assert_number_type(new_value, self.number_type)

    def __str__(self):
        return str(self._value)

    def __eq__(self, other: FixedNumber):
        if not isinstance(other, FixedNumber):
            raise TypeError(f"Cannot compare FixedNumber with {other.__class__.__name__}")
        if self.number_type != other.number_type:
            raise InvalidNumberTypeError(self, other.number_type)
        return self.value == other.value


def assert_number_type(number: int | float, number_type: NumberType) -> int | float:
    def can_be_represented_in_32_bits(f: float):
        numerator, denominator = f.as_integer_ratio()
        gcd = math.gcd(numerator, denominator)
        if gcd != 1:
            return False
        return -2147483648 <= numerator <= 2147483647 and -2147483648 <= denominator <= 2147483647

    # Type checking
    if (number_type == NumberType.i32 or number_type == NumberType.i64) and not isinstance(number, int):
        raise InvalidNumberTypeError(FixedNumber(number, None), number_type)
    elif (number_type == NumberType.f32 or number_type == NumberType.f64) and not isinstance(number, float):
        raise InvalidNumberTypeError(FixedNumber(number, None), number_type)

    # Overflow
    if number_type == NumberType.i32:
        number = number & 0xFFFFFFFF
        if number < 0:
            number = -0xF00000000 + number
    elif number_type == NumberType.i64:
        number = number & 0xFFFFFFFFFFFFFFFF
        if number < 0:
            number = -0xF0000000000000000 + number
    elif number_type == NumberType.f32 and not can_be_represented_in_32_bits(number):
        number = ctypes.c_float(number)
    return number


@singleton
class GlobalVariableWatch(VariableWatch):
    pass
