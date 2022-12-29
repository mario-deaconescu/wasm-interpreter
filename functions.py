from __future__ import annotations

import math
from dataclasses import dataclass

from enums import NumberType

@dataclass
class FixedNumber:
    _value: int | float
    number_type: NumberType

    def __post_init__(self) -> None:
        assert_number_type(self._value, self.number_type)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value: int | float):
        assert_number_type(new_value, self.number_type)
        self._value = new_value


def assert_number_type(number: int | float, number_type: NumberType):
    def can_be_represented_in_32_bits(f: float):
        numerator, denominator = f.as_integer_ratio()
        gcd = math.gcd(numerator, denominator)
        if gcd != 1:
            return False
        return -2147483648 <= numerator <= 2147483647 and -2147483648 <= denominator <= 2147483647

    match number_type:
        case NumberType.i32:
            assert (isinstance(number, int) and 0x7FFFFFFF >= number >= -0x80000000)
        case NumberType.i64:
            assert (isinstance(number, int) and 0x7FFFFFFFFFFFFFFF >= number >= -0x8000000000000000)
        case NumberType.f32:
            assert (isinstance(number, float) and can_be_represented_in_32_bits(number))
        case NumberType.f64:
            assert (isinstance(number, float)) # Python floats are already 64-bit
