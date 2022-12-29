from enums import NumberType
from expressions import SExpression, EXPORTED_FUNCTIONS
from functions import FixedNumber

with open('test.wast', 'r') as input_file:
    expr = input_file.read().replace('\n', '')
    expr = SExpression(expr)
    adder = EXPORTED_FUNCTIONS['add']
    print(adder.evaluate({}, FixedNumber(-6, NumberType.i32), FixedNumber(2, NumberType.i32)))
