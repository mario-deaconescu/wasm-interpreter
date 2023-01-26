from __future__ import annotations

from math import floor, ceil

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
        if self.operand.expression_name.startswith("0x"):
            if self.number_type == NumberType.i32 and (value & 0x80000000):
                value = -0x80000000 + (value & 0x7fffffff)
            elif self.number_type == NumberType.i64 and (value & 0x8000000000000000):
                value = -0x8000000000000000 + (value & 0x7fffffffffffffff)
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
        result = first_evaluation.value / second_evaluation.value
        if result < 0:
            result = ceil(result)
        else:
            result = floor(result)
        try:
            result = int(first_evaluation.value / second_evaluation.value)
        except OverflowError as e:
            raise OverflowError()  # TODO
        stack.push(FixedNumber(result, self.number_type))


class DivUnsignedExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        if second_evaluation.value == 0:
            raise DivisionByZeroError()
        stack.push(FixedNumber(first_evaluation.unsigned_value // second_evaluation.unsigned_value, self.number_type))
        # stack.push(FixedNumber(((first_evaluation.value & 0xffffffffffffffff)//(second_evaluation.value & 0xffffffffffffffff)) & 0xffffffffffffffff, self.number_type))
        # TODO cazul in care ai integer overflow


class AndExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(first_evaluation.value & second_evaluation.value, self.number_type))


class OrExpression(BinaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        def twos_complement(val: int, bits: int) -> int:
            if (val & (1 << (bits - 1))) != 0:
                val = val - (1 << bits)
            return val
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(twos_complement(first_evaluation.value | second_evaluation.value, 64), self.number_type))


class XorExpression(BinaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        def twos_complement(val: int, bits: int) -> int:
            if (val & (1 << (bits - 1))) != 0:
                val = val - (1 << bits)
            return val

        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        stack.push(FixedNumber(twos_complement(first_evaluation.value ^ second_evaluation.value, 64), self.number_type))


class ShlExpression(BinaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        if first_evaluation.number_type == NumberType.i32:
            if second_evaluation.value >= 0:
                stack.push(FixedNumber((first_evaluation.value * (2 ** (second_evaluation.value % 32))), self.number_type))
            else:
                stack.push(FixedNumber(first_evaluation.value * (2 ** (32 - abs(second_evaluation.value) % 32)), self.number_type))
        else:
            if second_evaluation.value >= 0:
                stack.push(FixedNumber((first_evaluation.value * (2 ** (second_evaluation.value % 64))), self.number_type))
            else:
                stack.push(FixedNumber(first_evaluation.value * (2 ** (64 - abs(second_evaluation.value) % 64)), self.number_type))


class ShrsExpression(BinaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        if first_evaluation.number_type == NumberType.i32:
            stack.push(FixedNumber(first_evaluation.value >> (abs(second_evaluation.value) % 32), self.number_type))
        else:
            stack.push(FixedNumber(first_evaluation.value >> (abs(second_evaluation.value) % 64), self.number_type))

class ShruExpression(BinaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        if first_evaluation.number_type == NumberType.i32:
            if second_evaluation.value >= 0 or second_evaluation.value % 32 == 0:
                result = first_evaluation.value >> (abs(second_evaluation.value) % 32)
                mask = 0xffffffff
                for i in range(abs(second_evaluation.value) % 32):
                    mask = mask - (1 << (32 - abs(second_evaluation.value)%32+i))
                result = result & mask
                stack.push(FixedNumber(result, self.number_type))
            else:
                result = first_evaluation.value >> (32 - abs(second_evaluation.value) % 32)
                mask = 0xffffffff
                for i in range(32 - abs(second_evaluation.value) % 32):
                    mask = mask - (1 << (32 - abs(second_evaluation.value) % 32 - i))

                result = result & mask
                stack.push(FixedNumber(result, self.number_type))
        else:
            if second_evaluation.value >= 0 or second_evaluation.value % 64 == 0:
                result = first_evaluation.value >> (abs(second_evaluation.value) % 64)
                mask = 0xffffffffffffffff
                for i in range(abs(second_evaluation.value) % 64):
                    mask = mask - (1 << (64 - abs(second_evaluation.value) % 64 + i))
                result = result & mask
                stack.push(FixedNumber(result, self.number_type))
            else:
                result = first_evaluation.value >> (64 - abs(second_evaluation.value) % 64)
                mask = 0xffffffffffffffff
                for i in range(64 - abs(second_evaluation.value) % 64):
                    mask = mask - (1 << (64 - abs(second_evaluation.value) % 64 - i))

                result = result & mask
                stack.push(FixedNumber(result, self.number_type))


class RotlExpression(BinaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        if first_evaluation.number_type == NumberType.i32:
            if second_evaluation.value >= 0:
                nshift = second_evaluation.value % 32
            else:
                nshift = 32 - abs(second_evaluation.value) % 32

            nshiftl = 32 - nshift

            result = first_evaluation.value >> (nshiftl)
            mask = 0xffffffff
            for i in range(nshiftl):
                mask = mask - (1 << (32 - nshiftl+i))
            result = result & mask

            stack.push(FixedNumber(((first_evaluation.value << nshift) & 0xffffffff) + result, self.number_type))

        else:
            if second_evaluation.value >= 0:
                nshift = second_evaluation.value % 64
            else:
                nshift = 64 - abs(second_evaluation.value) % 64

            nshiftl = 64 - nshift

            result = first_evaluation.value >> (nshiftl)
            mask = 0xffffffffffffffff
            for i in range(nshiftl):
                mask = mask - (1 << (64 - nshiftl+i))
            result = result & mask

            stack.push(FixedNumber(((first_evaluation.value << nshift) & 0xffffffffffffffff) + result, self.number_type))


class RotrExpression(BinaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation, second_evaluation = self.check_and_evaluate(stack, local_variables)
        if first_evaluation.number_type == NumberType.i32:
            if second_evaluation.value >= 0:
                nshift = second_evaluation.value % 32
            else:
                nshift = 32 - abs(second_evaluation.value) % 32

            nshiftl = 32 - nshift

            result = first_evaluation.value >> (nshift)
            mask = 0xffffffff
            for i in range(nshift):
                mask = mask - (1 << (32 - nshift+i))
            result = result & mask

            stack.push(FixedNumber(((first_evaluation.value << nshiftl) & 0xffffffff) + result, self.number_type))

        else:
            if second_evaluation.value >= 0:
                nshift = second_evaluation.value % 64
            else:
                nshift = 64 - abs(second_evaluation.value) % 64

            nshiftl = 64 - nshift

            result = first_evaluation.value >> (nshift)
            mask = 0xffffffffffffffff
            for i in range(nshift):
                mask = mask - (1 << (64 - nshift+i))
            result = result & mask

            stack.push(FixedNumber(((first_evaluation.value << nshiftl) & 0xffffffffffffffff) + result, self.number_type))


class CtzExpression(UnaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation = self.check_and_evaluate(stack, local_variables)
        def count_t(number):
            count = 0
            if number & 1 == 1:
                return 0
            while (number & 1) == 0:
                count += 1
                number = number >> 1
            return count
        if first_evaluation.value == 0:
            if first_evaluation.number_type == NumberType.i32:
                stack.push(FixedNumber(32, self.number_type))
            else:
                stack.push(FixedNumber(64, self.number_type))
        else:
            stack.push(FixedNumber(count_t(first_evaluation.value), self.number_type))

class ClzExpression(UnaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation = self.check_and_evaluate(stack, local_variables)
        def count_l(number, nBits):
            count = 0
            for i in range(nBits, 0, -1):
                if (number & (1 << i)) >> i == 0:
                    count += 1
                else:
                    break
            return count

        ok = 0
        if first_evaluation.number_type == NumberType.i32:
            nBits = 31
            if first_evaluation.value == 0:
                stack.push(FixedNumber(32, self.number_type))
                ok = 1

        else:
            nBits = 63
            if first_evaluation.value == 0:
                stack.push(FixedNumber(64, self.number_type))
                ok = 1
        if ok == 0:
            print(count_l(first_evaluation.value, nBits))
            stack.push(FixedNumber(count_l(first_evaluation.value, nBits), self.number_type))


class PopcntExpression(UnaryEvaluation):
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        first_evaluation = self.check_and_evaluate(stack, local_variables)
        number = first_evaluation.value
        count = 0
        if first_evaluation.value == 0:
            stack.push(FixedNumber(0, self.number_type))
        else:
            if first_evaluation.number_type == NumberType.i32:
                nBits = 31
            else:
                nBits = 63
            while number != 0:
                if (number & (1 << nBits)) >> nBits == 1:
                    count += 1
                if nBits == 63:
                    number = (number << 1) & 0xffffffffffffffff
                else:
                    number = (number << 1) & 0xffffffff
            stack.push(FixedNumber(count, self.number_type))

