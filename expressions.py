from __future__ import annotations

import re
from dataclasses import dataclass
from re import Match, Pattern

from enums import NumberType

@dataclass
class NumberVariable:
    number_type: NumberType
    name: str | None

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

    def __new__(cls, expression_string: str, *args, **kwargs) -> SExpression:
        instance = super().__new__(cls)

        # Check if expression has surrounding parentheses
        match: Match[str] | None = re.fullmatch('\(.*\)', expression_string)
        if match is None:
            # No surrounding parentheses
            instance.expression_type = expression_string
            return instance

        # Remove redundant parentheses
        expression_string = expression_string[1:-1].strip()

        # Separate name from children
        children_string: str = ""
        split_expression: list[str] = expression_string.split(' ', 1)
        instance.expression_type = split_expression[0]
        if len(split_expression) > 1:
            children_string = split_expression[1]

        c = []
        for x in SExpression.get_parentheses(children_string):
            c.append(SExpression(x))
        instance.children = c

        # Check if expression has a name
        if len(instance.children) > 0 and instance.children[0].expression_type[0] == '$':
            # The name is the variable name without the '$'
            instance.name = instance.children[0].expression_type[1:]
            # Remove the variable name from the children
            instance.children = instance.children[1:]

        # Check expression type
        match instance.expression_type:
            case 'module':
                instance.__class__ = Module
            case 'func':
                instance.__class__ = FunctionExpression
            case 'export':
                instance.__class__ = ExportExpression
            case 'param':
                instance.__class__ = ParamExpression
            case 'result':
                instance.__class__ = ResultExpression

        return instance

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __str__(self) -> str:
        return f'{self.expression_type}' + (
            f'({self.name})' if self.name is not None else '')

    def __repr__(self, level=0) -> str:
        return '\t' * level + '- ' + str(self) + '\n' + ''.join([child.__repr__(level + 1) for child in self.children])


class Module(SExpression):
    pass


class FunctionExpression(SExpression):
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parameters = []
        if len(self.children) > 0:
            if isinstance(self.children[0], ExportExpression):
                export_expression: ExportExpression = self.children[0]
                self.export_as = export_expression.export_name
                self.children = self.children[1:]
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


class ExportExpression(SExpression):
    export_name: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if len(self.children) != 1:
            raise ValueError(f"Export expression has incorrect number of parameters ({len(self.children)})")
        # Remove "" from name
        self.export_name = self.children[0].expression_type[1:-1]
        self.children = []


class NumberExpression(SExpression):
    number_type: NumberType

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if len(self.children) != 1:
            raise ValueError(f"Number expression has incorrect number of parameters ({len(self.children)})")
        match self.children[0].expression_type:
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


class ParamExpression(NumberExpression):
    pass


class ResultExpression(NumberExpression):
    pass
