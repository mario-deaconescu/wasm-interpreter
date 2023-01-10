from argparse import ArgumentParser, Namespace
from os.path import exists
from typing import Generator

from enums import NumberType
from custom_exceptions import InvalidNumberTypeError
from expressions import SExpression, EXPORTED_FUNCTIONS, AssertInvalidExpression, AssertExpression
from functions import FixedNumber


FAIL_CODE = '\033[91m'
ENDC = '\033[0m'


# Generator for more efficient parsing
def read_expressions(input_file_name: str) -> Generator[SExpression, None, None]:
    with open(input_file_name, 'r') as input_file:
        expression_string = input_file.read().replace('\n', '')
    for string in SExpression.get_parentheses(expression_string):
        yield SExpression(string)


def check_asserts(input_file_name: str) -> None:
    number_of_correct_assertions: int = 0
    assertion_index: int = 0
    for expression in read_expressions(input_file_name):
        if isinstance(expression, AssertExpression):
            asserted: bool = expression.assert_expression()
            if asserted:
                number_of_correct_assertions += 1
                print(f'Assertion #{assertion_index} of type "{expression}" was successful!')
            else:
                print(f'{FAIL_CODE}Assertion #{assertion_index} of type "{expression}" was unsuccessful!{ENDC}')
            assertion_index += 1
    print()
    print(f'Correct assertions: {number_of_correct_assertions}/{assertion_index}.')

if __name__ == '__main__':

    parser: ArgumentParser = ArgumentParser(
        prog="WAST Interpreter",
        description="Interpret Web Assembly Text (.wast) files using Python 3.10",
        epilog="Made by Deaconescu Mario (si speram ca Miu Tudor, and Berbece David)"  # TODO
    )

    parser.add_argument("input_file")

    args: Namespace = parser.parse_args()

    if not exists(args.input_file):
        raise FileNotFoundError(f'File {args.input_file} not found!')

    check_asserts(args.input_file)
