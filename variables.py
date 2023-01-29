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
        if not (name is not None and isinstance(name, str) and name.startswith('~')):
            self._variables[self._variable_counter] = value
            self._variable_counter += 1
        if name is not None:
            if isinstance(name, str) and not name.startswith('$'):
                name = '$' + name
            self._variables[name] = value

    def __setitem__(self, key: str | int, value):
        if isinstance(key, int):
            self._variables[key] = value
        else:
            if key.startswith('$'):
                key = key[1:]
            self._variables['$' + key] = value

    def __contains__(self, item: str | int) -> bool:
        if isinstance(item, str) and not item.startswith('$'):
            item = '$' + item
        return item in self._variables


@singleton
class Stack:
    _stacks: list[list[Any]] = [[]]
    _stack_size: int = 1024

    @property
    def _current_stack(self) -> list[Any]:
        return self._stacks[-1]

    def init(self, stack_size: int = 1024):
        self._stacks = [[]]
        self._stack_size = stack_size

    def pop(self) -> Any:
        if self.get_total_size() == 0:
            raise StackEmptyError()
        if len(self._current_stack) == 0:
            return self.get_previous_stack().pop()
        return self._current_stack.pop()

    def push(self, value: Any) -> None:
        if self.get_total_size() == self._stack_size:
            raise StackOverflowError(self._stack_size)
        self._current_stack.append(value)

    def __getitem__(self, item: int) -> Any:
        return self._current_stack[-item - 1]

    def __del__(self):
        self._stacks = [[]]

    def __len__(self):
        return len(self._current_stack)

    def expand(self, size: int):
        self._current_stack += [None] * size

    def contract(self, size: int):
        self._current_stack = self._current_stack[:-size]

    def size_to(self, size: int):
        if len(self._current_stack) > size:
            self.contract(len(self._current_stack) - size)
        elif len(self._current_stack) < size:
            self.expand(size - len(self._current_stack))

    @_current_stack.setter
    def _current_stack(self, value):
        self._stacks[-1] = value

    def push_stack(self):
        self._stacks.append([])

    def pop_stack(self):
        old_stack = self._stacks.pop()
        if len(self._stacks) != 0:
            self._current_stack += old_stack

    def get_previous_stack(self):
        return self._stacks[-2]

    def get_total_size(self) -> int:
        return sum([len(stack) for stack in self._stacks])


@dataclass
class FixedNumber:
    _value: int | float
    number_type: NumberType

    def __post_init__(self) -> None:
        if self._value is not None:
            self._value = assert_number_type(self._value, self.number_type)

    @property
    def value(self) -> int | float:
        return self._value

    @property
    def unsigned_value(self) -> int:
        if self.number_type in [NumberType.f32, NumberType.f64]:
            return self._value
        if self.number_type == NumberType.i32:
            mask = 0x80000000
        else:
            mask = 0x8000000000000000
        return (self._value & (mask - 1)) + (self._value & mask)

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

    def __abs__(self) -> int | float:
        return self.unsigned_value

    @staticmethod
    def can_be_reprezented_in_32_bits(number: int):
        return -2147483648 <= number <= 2147483647

    @staticmethod
    def can_be_reprezented_in_64_bits(number: int):
        return -9223372036854775808 <= number <= 9223372036854775807


def assert_number_type(number: int | float, number_type: NumberType) -> int | float:
    def can_be_represented_in_32_bits(f: float):
        numerator, denominator = f.as_integer_ratio()
        gcd = math.gcd(numerator, denominator)
        if gcd != 1:
            return False
        return -2147483648 <= numerator <= 2147483647 and -2147483648 <= denominator <= 2147483647

    if number_type == NumberType.v128:
        return number

    # Type checking
    if (number_type == NumberType.i32 or number_type == NumberType.i64) and not isinstance(number, int):
        raise InvalidNumberTypeError(FixedNumber(number, None), number_type)
    elif (number_type == NumberType.f32 or number_type == NumberType.f64) and not (
            isinstance(number, float) or isinstance(number, int)):
        raise InvalidNumberTypeError(FixedNumber(number, None), number_type)

    # Overflow
    if number_type == NumberType.i32:
        number = (number & 0x7FFFFFFF) + (number & 0x80000000) * (1 if number > 0 else -1)
    elif number_type == NumberType.i64:
        number = (number & 0x7FFFFFFFFFFFFFFF) + (number & 0x8000000000000000) * (1 if number > 0 else -1)
    elif number_type == NumberType.f32 and not can_be_represented_in_32_bits(number):
        number = ctypes.c_float(number)
    return number


@dataclass()
class GlobalVariable:
    mutable: bool
    value: FixedNumber


@singleton
class GlobalVariableWatch:
    _variable_counter: int = 0
    _variables: dict[int | str, GlobalVariable] = {}

    def __init__(self):
        self._variable_counter = 0
        self._variables = {}

    def __getitem__(self, item):
        if isinstance(item, str) and not item.startswith('$'):
            item = '$' + item
        return self._variables[item]

    def add_variable(self, value, mutable: bool, name=None) -> None:
        self._variables[self._variable_counter] = GlobalVariable(mutable, value)
        self._variable_counter += 1
        if name is not None:
            if isinstance(name, str) and not name.startswith('$'):
                name = '$' + name
            self._variables[name] = GlobalVariable(mutable, value)

    def __setitem__(self, key: str | int, value):
        if isinstance(key, int):
            self._variables[key].value = value
        else:
            if key.startswith('$'):
                key = key[1:]
            self._variables['$' + key].value = value

    def __contains__(self, item: str | int) -> bool:
        if isinstance(item, str) and not item.startswith('$'):
            item = '$' + item
        return item in self._variables


@singleton
class Memory:
    PAGE_SIZE = 65536
    _memory: bytearray = bytearray()

    def __init__(self, pages: int = 1):
        super().__init__()
        self._memory = bytearray(pages * self.PAGE_SIZE)

    def grow(self, pages: int):
        self._memory += bytearray(pages * self.PAGE_SIZE)

    @property
    def allocated(self):
        return len(self._memory) // self.PAGE_SIZE

    def __setitem__(self, index: int, value: FixedNumber):
        if index < 0:
            raise IndexError(f"Cannot access memory at negative index {index}")
        if index >= len(self._memory):
            raise IndexError(f"Cannot access memory at index {index} because it is out of bounds")
        if value.number_type == NumberType.i32:
            for byte_index in range(4):
                self._memory[index + byte_index] = (value.unsigned_value >> (8 * byte_index)) & 0xFF
        elif value.number_type == NumberType.i64:
            for byte_index in range(8):
                self._memory[index + byte_index] = (value.unsigned_value >> (8 * byte_index)) & 0xFF
        elif value.number_type == NumberType.f32:
            for byte_index in range(4):
                self._memory[index + byte_index] = (value.value >> (8 * byte_index)) & 0xFF
        elif value.number_type == NumberType.f64:
            for byte_index in range(8):
                self._memory[index + byte_index] = (value.value >> (8 * byte_index)) & 0xFF

    def __getitem__(self, index_tuple: tuple[int, NumberType]) -> FixedNumber:
        index, number_type = index_tuple
        if index < 0:
            raise IndexError(f"Cannot access memory at negative index {index}")
        if index >= len(self._memory):
            raise IndexError(f"Cannot access memory at index {index} because it is out of bounds")
        if number_type == NumberType.i32:
            return FixedNumber(int.from_bytes(self._memory[index:index + 4], byteorder='little', signed=True),
                               NumberType.i32)
        elif number_type == NumberType.i64:
            return FixedNumber(int.from_bytes(self._memory[index:index + 8], byteorder='little', signed=True),
                               NumberType.i64)
        elif number_type == NumberType.f32:
            return FixedNumber(
                ctypes.c_float(int.from_bytes(self._memory[index:index + 4], byteorder='little', signed=True)).value,
                NumberType.f32)
        elif number_type == NumberType.f64:
            return FixedNumber(
                ctypes.c_double(int.from_bytes(self._memory[index:index + 8], byteorder='little', signed=True)).value,
                NumberType.f64)
