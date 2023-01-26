from __future__ import annotations

import re
import sys

from abc import abstractmethod
from typing import Pattern, Type

from custom_exceptions import *
from evaluations import Evaluation
from expressions import SExpression, ModuleExpression
from variables import VariableWatch, FixedNumber, Stack, GlobalVariableWatch


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

    instantiation_errors: list[Type[WebAssemblyException]] = None

    def __init__(self):
        super().__init__()

    def assert_expression(self) -> bool:
        # Check if return type is string
        string_regex: Pattern[str] = re.compile('"([a-zA-Z ]+)"')
        if not string_regex.fullmatch(self.assert_return.expression_name):
            raise TypeError(
                f"Invalid assert result: Expected string, got {self.assert_operand.expression_name}")

        exception_name: str = self.assert_return.expression_name.strip('"')  # Remove " " from name

        expected_exceptions: list[Type] = [getattr(sys.modules[__name__], exception_name) for exception_name in
                                           EXCEPTION_NAMES[exception_name]]
        if self.instantiation_errors is not None:
            for error in self.instantiation_errors:
                for e in expected_exceptions:
                    if isinstance(error, e):
                        return True

        if not isinstance(self.assert_operand, ModuleExpression):
            raise TypeError(
                f"Invalid assert operand: Expected Module, got {self.assert_operand.__class__.__name__}")

        # try:
        #     self.assert_operand.assert_correctness(VariableWatch())
        # except WebAssemblyException as exception:
        #     # Check if it's the right exception
        #     for e in expected_exceptions:
        #         if isinstance(exception, e):
        #             return True
        return False


class AssertReturnExpression(AssertExpression):

    def assert_expression(self) -> bool:
        if not isinstance(self.assert_operand, Evaluation):
            raise TypeError(
                f"Invalid assert operand: Expected Evaluation, got {self.assert_operand.__class__.__name__}")
        if not isinstance(self.assert_return, Evaluation):
            raise TypeError(f"Invalid assert result: Expected Evaluation, got {self.assert_return.__class__.__name__}")

        stack: Stack = Stack()
        if not isinstance(self.assert_operand, Evaluation):
            raise TypeError(f"Invalid assert operand: Expected Evaluation, got {self.assert_operand.__class__.__name__}")
        evaluation: Evaluation = self.assert_operand
        evaluation.evaluate(stack, VariableWatch())
        result: FixedNumber = stack.pop()

        if not isinstance(self.assert_return, Evaluation):
            raise TypeError(f"Invalid assert result: Expected Evaluation, got {self.assert_return.__class__.__name__}")
        expected_evaluation: Evaluation = self.assert_return
        expected_evaluation.evaluate(stack, VariableWatch())
        expected_result: FixedNumber = stack.pop()

        return abs(result) == abs(expected_result)


class AssertTrapExpression(AssertExpression):

    def assert_expression(self) -> bool:
        if not isinstance(self.assert_operand, Evaluation):
            raise TypeError(
                f"Invalid assert operand: Expected Evaluation, got {self.assert_operand.__class__.__name__}")

        # Check if return type is string
        string_regex: Pattern[str] = re.compile('"([a-zA-Z ]+)"')
        if not string_regex.fullmatch(self.assert_return.expression_name):
            raise TypeError(
                f"Invalid assert result: Expected string, got {self.assert_operand.expression_name}")

        exception_name: str = self.assert_return.expression_name.strip('"')  # Remove " " from name

        try:
            self.assert_operand.evaluate(Stack(), VariableWatch(), GlobalVariableWatch())
        except WebAssemblyException as exception:
            # Check if it's the right exception
            expected_exceptions: list[Type] = [getattr(sys.modules[__name__], exception_name) for exception_name in EXCEPTION_NAMES[exception_name]]
            for e in expected_exceptions:
                if isinstance(exception, e):
                    return True
        return False
