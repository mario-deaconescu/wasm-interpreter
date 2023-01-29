from __future__ import annotations

from custom_exceptions import InvalidSyntaxError
from enums import NumberType
from expressions import SExpression
from variables import Stack


def main():
    pass


if __name__ == '__main__':
    main()


class NumberTypeExpression(SExpression):
    number_types: list[NumberType]

    def __init__(self, **kwargs) -> None:
        super().__init__()
        if len(self.children) != 1:
            raise InvalidSyntaxError(f"Number expression has incorrect number of parameters ({len(self.children)})")
        self.number_types = [NumberType(type_string) for type_string in self.children[0].expression_name.split(" ")]
        self.children = []


class ResultExpression(NumberTypeExpression):
    pass


class ParamExpression(NumberTypeExpression):

    def __init__(self, **kwargs):
        super().__init__()
        # Stack().expand(len(self.number_types))
