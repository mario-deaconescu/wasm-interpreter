from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING

from custom_exceptions import InvalidSyntaxError
if TYPE_CHECKING:
    pass
from variables import VariableWatch


class SExpression:
    expression_name: str = ""
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

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None):
        for child in self.children:
            child.assert_correctness(local_variables)

    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return f'{self.expression_name}' + (
            f'({self.name})' if self.name is not None else '')

    def __repr__(self, level=0) -> str:
        return '\t' * level + '- ' + str(self) + '\n' + ''.join([child.__repr__(level + 1) for child in self.children])


class ModuleExpression(SExpression):
    pass


class ExportExpression(SExpression):
    export_name: str

    def __init__(self, _=None) -> None:
        super().__init__()
        if len(self.children) != 1:
            raise InvalidSyntaxError(f"Export expression has incorrect number of parameters ({len(self.children)})")
        # Remove "" from name
        self.export_name = self.children[0].expression_name[1:-1]
        self.children = []

