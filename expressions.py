from __future__ import annotations

import re
from re import Match, Pattern


class SExpression:
    expression_type: str
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
                    raise ValueError(f'Expression "{expression}" has invalid parentheses')
                break

            if expression[next_parenthesis.start()] == ')':
                open_parentheses -= 1
                if open_parentheses < 0:
                    raise ValueError(f'Expression "{expression}" has invalid parentheses')
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
            # We found our parentheses
            return parentheses

        # Check if there is a variable name
        if expression[0] == '$':
            return expression.split(' ', 1)

        return [expression]

    def __init__(self, expression_string: str) -> None:
        # Check if expression has surrounding parentheses
        match: Match[str] | None = re.fullmatch('\(.*\)', expression_string)
        if match is None:
            # No surrounding parentheses
            self.expression_type = expression_string
            return

        # Remove redundant parentheses
        expression_string = expression_string[1:-1].strip()

        # Separate name from children
        children_string: str = ""
        split_expression: list[str] = expression_string.split(' ', 1)
        self.expression_type = split_expression[0]
        if len(split_expression) > 1:
            children_string = split_expression[1]
        self.children = [SExpression(subexpression) for subexpression in SExpression.get_parentheses(children_string)]

        # Check if expression has a name
        if self.children[0].expression_type[0] == '$':
            # The name is the variable name without the '$'
            self.name = self.children[0].expression_type[1:]
            # Remove the variable name from the children
            self.children = self.children[1:]

        # Check expression type
        match self.expression_type:
            case 'module':
                self.__class__ = Module
            case 'func':
                self.__class__ = Function

    def __str__(self) -> str:
        return f'{self.expression_type}[{self.__class__.__name__}]' + (
            f'({self.name})' if self.name is not None else '')

    def __repr__(self, level=0) -> str:
        return '\t' * level + '- ' + str(self) + '\n' + ''.join([child.__repr__(level + 1) for child in self.children])


class Module(SExpression):
    pass


class Function(SExpression):
    pass
