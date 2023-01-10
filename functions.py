from __future__ import annotations

import math
from dataclasses import dataclass

from custom_exceptions import InvalidNumberTypeError
from enums import NumberType


@dataclass
class FixedNumber:
    _value: int | float
    number_type: NumberType

    def __post_init__(self) -> None:
        assert_number_type(self._value, self.number_type)

    @property
    def value(self) -> int | float:
        return self._value

    @value.setter
    def value(self, new_value: int | float):
        assert_number_type(new_value, self.number_type)
        self._value = new_value

    def __str__(self):
        return str(self._value)

    def __eq__(self, other: FixedNumber):
        if not isinstance(other, FixedNumber):
            raise TypeError(f"Cannot compare FixedNumber with {other.__class__.__name__}")
        if self.number_type != other.number_type:
            raise InvalidNumberTypeError(self, other.number_type)
        return self.value == other.value


def assert_number_type(number: int | float, number_type: NumberType):
    def can_be_represented_in_32_bits(f: float):
        numerator, denominator = f.as_integer_ratio()
        gcd = math.gcd(numerator, denominator)
        if gcd != 1:
            return False
        return -2147483648 <= numerator <= 2147483647 and -2147483648 <= denominator <= 2147483647

    match number_type:
        case NumberType.i32:
            if not isinstance(number, int) and 0x7FFFFFFF >= number >= -0x80000000:
                raise InvalidNumberTypeError(FixedNumber(number, None), number_type)
        case NumberType.i64:
            if not isinstance(number, int) and 0x7FFFFFFFFFFFFFFF >= number >= -0x8000000000000000:
                raise InvalidNumberTypeError(FixedNumber(number, None), number_type)
        case NumberType.f32:
            if not isinstance(number, float) and can_be_represented_in_32_bits(number):
                raise InvalidNumberTypeError(FixedNumber(number, None), number_type)
        case NumberType.f64:
            if not isinstance(number, float): # Python floats are already 64-bit
                raise InvalidNumberTypeError(FixedNumber(number, None), number_type)
