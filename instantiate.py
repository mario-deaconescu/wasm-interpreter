from __future__ import annotations

import re
import sys
from re import Match

from expressions import *
from function import *
from evaluations import *
from operations import *
from assertions import *
from stackoperations import *
from logic import *

CLASSES_DICT: dict[str, str] = {
    'module': 'ModuleExpression',
    'func': 'FunctionExpression',
    'export': 'ExportExpression',
    'param': 'ParamExpression',
    'result': 'ResultExpression',
    'local.get': 'LocalGetter',
    'local.set': 'LocalSetter',
    'local.tee': 'LocalTee',
    'local': 'LocalExpression',
    'global.get': 'GlobalGetter',
    'global.set': 'GlobalSetter',
    'load': 'LoadExpression',
    'assert_return': 'AssertReturnExpression',
    'assert_invalid': 'AssertInvalidExpression',
    'assert_trap': 'AssertTrapExpression',
    'assert_malformed': 'AssertInvalidExpression',
    'add': 'AddExpression',
    'sub': 'SubExpression',
    'and': 'AndExpression',
    'or': 'OrExpression',
    'xor': 'XorExpression',
    'shl': 'ShlExpression',
    'shr_s': 'ShrsExpression',
    'shr_u': 'ShruExpression',
    'rotl': 'RotlExpression',
    'rotr': 'RotrExpression',
    'clz': 'ClzExpression',
    'popcnt': 'PopcntExpression',
    'eq': 'EqExpression',
    'eqz': 'EqzExpression',
    'ne': 'NeExpression',
    'lt_s': 'LtsExpression',
    'lt_u': 'LtuExpression',
    'le_s': 'LesExpression',
    'le_u': 'LeuExpression',
    'gt_s': 'GtsExpression',
    'gt_u': 'GtuExpression',
    'ge_s': 'GesExpression',
    'ge_u': 'GeuExpression',
    'f32.gt': 'F32GTExpression',
    'ctz': 'CtzExpression',
    'extend_i32_u': 'Extendi32uExpression',
    'extend8_s': 'Extend8Expression',
    'extend16_s': 'Extend16Expression',
    'extend32_s': 'Extend32Expression',
    'div_s': 'DivSignedExpression',
    'div_u': 'DivUnsignedExpression',
    'rem_s': 'RemsExpression',
    'rem_u': 'RemuExpression',
    'const': 'ConstExpression',
    'drop': 'DropExpression',
    'block': 'BlockExpression',
    'loop': 'LoopExpression',
    'if': 'IfExpression',
    'then': 'ThenExpression',
    'else': 'ElseExpression',
    'return': 'ReturnExpression',
    'select': 'SelectExpression',
    'call': 'CallExpression',
    'tablefuncref': 'TableFunctionExpression',
    'type': 'TypeExpression',
    'call_indirect': 'CallIndirectExpression',
    'memory.grow': 'MemoryGrowExpression',
    'store': 'StoreExpression',
    'mul': 'MulExpression',
    'nop': 'NOPExpression',
    'elem': 'ElementExpression',
    'br': 'BranchExpression',
    'br_if': 'BranchIfExpression',
    'br_table': 'BranchTableExpression',
    'gt': 'F32GTExpression',
    'unreachable': 'UnreachableExpression',
    'global': 'GlobalExpression',
}

WARNING_CODE = '\033[93m'
FAIL_CODE = '\033[91m'
ENDC = '\033[0m'


class ExpressionInstantiater:
    temporary_variables: VariableWatch = None

    def __init__(self):
        self.temporary_variables = VariableWatch()
        self.temporary_variables.add_variable(False, '~typing~')
        self.temporary_variables.add_variable(False, '~assert~')

    def create_expression(self, expression_string: str, **kwargs) -> SExpression:
        instance = SExpression()

        # Check if expression has surrounding parentheses
        parentheses_match: Match[str] | None = re.fullmatch(r'\(.*\)', expression_string)
        if parentheses_match is None:
            # No surrounding parentheses
            instance.expression_name = expression_string
            return instance

        # Remove redundant parentheses
        expression_string = expression_string[1:-1].strip()

        # Separate name from children
        children_string: str = ""

        # Special case for "table funcref"
        if expression_string.startswith("table funcref"):
            expression_string = expression_string.replace("table funcref", "tablefuncref")

        # Special case for "invoke"
        if expression_string.startswith('invoke ') \
                or expression_string.startswith('call ') \
                or expression_string.startswith('type ') \
                or expression_string.startswith('local '):
            if '(' in expression_string or ')' in expression_string:
                triple_expression: list[str] = expression_string.split(' ', 2)
            else:
                triple_expression: list[str] = expression_string.split(' ', 1) + ['']
            split_expression: tuple[str, ...] = (f'{triple_expression[0]} {triple_expression[1]}', triple_expression[2])
            if expression_string.startswith('invoke'):
                instance.__class__ = InvokeExpression
            elif expression_string.startswith('call'):
                instance.__class__ = CallExpression
            elif expression_string.startswith('type'):
                instance.__class__ = TypeExpression
                self.temporary_variables.add_variable(True, '~typing~')
            elif expression_string.startswith('local'):
                instance.__class__ = LocalExpression
        else:
            split_expression: tuple[str, ...] = tuple(expression_string.split(' ', 1))
        instance.expression_name = split_expression[0]
        if len(split_expression) > 1:
            children_string = split_expression[1]
        if children_string.startswith('$'):
            # This is a variable name
            if ' ' not in children_string:
                instance.name = children_string[1:]
            else:
                instance.name, children_string = children_string.split(' ', 1)
                instance.name = instance.name[1:]

        # Special case fot quote
        if children_string.startswith('quote'):
            # children_string = children_string.split(' ', 1)[1].strip('"')
            children_string = re.sub('quote +', '', children_string)
            children_string = re.sub('"([^"]+)" *', r'\1 ', children_string)
            raise UnexpectedTokenError(f'Unexpected token: {children_string}')

        children_parentheses: list[str] = SExpression.get_parentheses(children_string)
        if len(children_parentheses) > 0 and children_parentheses[0].startswith('$'):
            # This is a variable name
            instance.name = children_parentheses[0][1:]
            children_parentheses.pop(0)

        # Check if it's a predefined function
        new_type: str = instance.expression_name
        if re.fullmatch(r'.{3}\.([a-z_0-9]+)', instance.expression_name) is not None:
            new_type = new_type[4:]

        # Check expression type
        if new_type in CLASSES_DICT.keys():
            instance.__class__ = getattr(sys.modules[__name__], CLASSES_DICT[new_type])

        if instance.__class__ == SExpression:
            if kwargs.get('debug', False):
                raise NotImplementedError(f'Not implemented {instance.expression_name}!')
            else:
                with open('not_implemented.txt', 'a') as f:
                    f.write(f'{instance.expression_name}\n')
                print(f'{WARNING_CODE}Not implemented {instance.expression_name}!{ENDC}')

        initial_stack_size: int = len(Stack())
        restore_stack: bool = False
        if isinstance(instance, FunctionExpression) or \
                isinstance(instance, BlockExpression) or \
                isinstance(instance, LoopExpression) or \
                isinstance(instance, IfExpression) or \
                isinstance(instance, CallExpression):
            restore_stack = True
            #if not isinstance(instance, IfExpression):
            Stack().push_stack()

        if isinstance(instance, AssertInvalidExpression):
            self.temporary_variables.add_variable(True, '~assert~')

        c = []
        if_parsed_type: bool = False
        if_parsed_condition: bool = False
        for x in children_parentheses:
            try:
                c.append(self.create_expression(x))
            except WebAssemblyException as e:
                if not isinstance(instance, AssertInvalidExpression):
                    raise e
                if instance.instantiation_errors is None:
                    instance.instantiation_errors = []
                instance.instantiation_errors.append(e)
                temp = SExpression()
                temp.expression_name = "~invalid~"
                c.append(temp)
            if self.temporary_variables['~assert~'] and isinstance(c[-1], BranchExpression):
                break
            if isinstance(instance, IfExpression):
                if isinstance(c[-1], ParamExpression) and not if_parsed_type:
                    params: ParamExpression = c[-1]
                    if len(Stack().get_previous_stack()) > 0 and isinstance(Stack().get_previous_stack()[-1], NumberType) and len(params.number_types) == 1 and Stack().get_previous_stack()[-1] != params.number_types[0]:
                        raise InvalidNumberTypeError(FixedNumber(None, params.number_types[0]), Stack().get_previous_stack()[-1])
                    for _ in params.number_types:
                        if len(Stack().get_previous_stack()) == 0:
                            # No parameters
                            raise InvalidNumberTypeError(None, None)
                        Stack().get_previous_stack().pop()
                        Stack().expand(1)
                elif isinstance(c[-1], TypeExpression):
                    if_parsed_type = True
                    type_expression: TypeExpression = c[-1]
                    for _ in type_expression.parameters:
                        Stack().get_previous_stack().pop()
                        Stack().expand(1)
                elif not if_parsed_condition and not isinstance(c[-1], ThenExpression) and not isinstance(c[-1], ElseExpression) and not isinstance(c[-1], ResultExpression) and not isinstance(c[-1], TypeExpression):
                    if_parsed_condition = True
                    Stack().contract(1)
                elif isinstance(c[-1], ThenExpression):
                    instance.then_results = c[-1].result_size
                elif isinstance(c[-1], ElseExpression):
                    instance.else_results = c[-1].result_size

        instance.children = c

        # Check if expression has a name
        if len(instance.children) > 0 and instance.children[0].expression_name[0] == '$':
            # The name is the variable name without the '$'
            instance.name = instance.children[0].expression_name[1:]
            # Remove the variable name from the children
            instance.children = instance.children[1:]

        instance.__init__(variables=self.temporary_variables)

        if isinstance(instance, IfExpression) and not if_parsed_condition:
            if len(Stack()) == 0:
                raise InvalidNumberTypeError(None, None)

            Stack().contract(1)

        if restore_stack:
            Stack().pop_stack()
        elif isinstance(instance, ThenExpression) or isinstance(instance, ElseExpression):  # Reset local stack
            Stack().size_to(initial_stack_size)
        if instance.name is not None:
            self.temporary_variables.add_variable(instance, instance.name)
        return instance
