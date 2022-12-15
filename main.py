from expressions import SExpression

with open('test.wast', 'r') as input_file:
    expr = input_file.read().replace('\n', '')
    expr = SExpression(expr)
    print(repr(expr))