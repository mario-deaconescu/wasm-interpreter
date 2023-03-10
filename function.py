from __future__ import annotations

from enum import Enum

from custom_exceptions import InvalidFunctionSignatureError, UnknownFunctionError, EmptyOperandError, \
    UndefinedElementError, InvalidNumberTypeError, InvalidFunctionResultError
from enums import NumberType
from evaluations import Evaluation, UnaryEvaluation, EvaluationReport
from expressions import ExportExpression, SExpression
from number_types import ResultExpression, ParamExpression
from singleton import singleton
from variables import VariableWatch, FixedNumber, NumberVariable, Stack, GlobalVariableWatch


@singleton
class FunctionRegistry:
    functions: list[FunctionExpression] = []

    def clear(self) -> None:
        self.functions = []

    def register_function(self, function: FunctionExpression) -> None:
        self.functions.append(function)

    def get_function(self, index: int) -> FunctionExpression:
        if index >= len(self.functions):
            raise UndefinedElementError(f'Undefined element at index {index}')
        return self.functions[index]


class FunctionExpression(Evaluation):
    export_as: str = None
    parameters: list[NumberVariable]
    result_types: list[NumberType] | None = None

    def __str__(self) -> str:
        representation: str = super().__str__()
        parameter_representations: list[str] = []
        for parameter in self.parameters:
            if parameter.name is None:
                parameter_representations.append(parameter.number_type.value)
            else:
                parameter_representations.append(f"{parameter.name}: {str(parameter.number_type.value)}")
        representation += f"({', '.join(parameter_representations)})"
        representation += f" -> {self.result_types if self.result_types is not None else 'None'}"
        representation += f' (exported as "{self.export_as}")'
        return representation

    def __init__(self, variables=None) -> None:
        super().__init__()
        self.parameters = []
        if len(self.children) > 0:
            if isinstance(self.children[0], ExportExpression):
                export_expression: ExportExpression = self.children[0]
                self.export_as = export_expression.export_name
                self.children = self.children[1:]
                EXPORTED_FUNCTIONS[self.export_as] = self
        child_index: int = 0
        while child_index < len(self.children) and isinstance(self.children[child_index], ParamExpression):
            parameter_expression: ParamExpression = self.children[child_index]
            self.parameters += [NumberVariable(number_type, parameter_expression.name) for number_type in
                                parameter_expression.number_types]
            child_index += 1
        # Remove parameters from children
        self.children = self.children[child_index:]
        if len(self.children) > 0:
            if isinstance(self.children[0], ResultExpression):
                result_expression: ResultExpression = self.children[0]
                self.result_types = result_expression.number_types
                self.children = self.children[1:]
        if self.result is not None:
            self.result_types = self.result.number_types
        if self.result_types is not None:
            if not variables['~typing~'] and len(self.result_types) != len(Stack()):
                raise InvalidFunctionResultError(self, *self.result_types)
            Stack().contract(len(self.result_types))
        else:
            if not variables['~typing~'] and len(Stack()) != 0:
                raise InvalidFunctionResultError(self)

    def initialize_parameters(self, local_variables: VariableWatch, global_variables: GlobalVariableWatch,
                              *args: NumberVariable | FixedNumber) \
            -> VariableWatch:
        new_local_variables = VariableWatch()
        # Check parameters
        if len(args) != len(self.parameters):
            raise InvalidFunctionSignatureError(self, *args)
        for index, arg in enumerate(args):
            if self.parameters[index].number_type != arg.number_type:
                raise TypeError("Invalid parameter type")
            new_local_variables.add_variable(arg, self.parameters[index].name)
        for expression in self.children:
            if not isinstance(expression, Evaluation):
                raise TypeError("Expression can not be evaluated")
        return new_local_variables
    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None,
                 *args: FixedNumber) -> None:
        super().evaluate(stack, local_variables, global_variables)
        # Check parameters
        local_variables = self.initialize_parameters(local_variables, global_variables, *args)
        for evaluation in self.children:
            report: EvaluationReport | None = evaluation.evaluate(stack, local_variables)
            if report is not None and report.signal_return:
                break


class InvokeExpression(Evaluation):
    function: FunctionExpression = None

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.expression_name, function_name = self.expression_name.split(' ')
        function_name = function_name.strip('"')
        if function_name not in EXPORTED_FUNCTIONS:
            raise UnknownFunctionError(function_name)

        self.function = EXPORTED_FUNCTIONS[function_name]

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        parameters: list[FixedNumber] = []
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)
            parameters.append(stack.pop())
        self.function.evaluate(stack, local_variables, global_variables, *parameters)

    def __str__(self):
        return f'{super().__str__()}({self.function.export_as})'


class CallExpression(Evaluation):
    function_identifier: int | str = None
    function: FunctionExpression = None

    def __init__(self, variables=None) -> None:
        super().__init__()
        self.expression_name, self.function_identifier = self.expression_name.split(' ')
        try:
            self.function_identifier = int(self.function_identifier)
        except ValueError:
            pass
        try:
            self.function: FunctionExpression = variables[self.function_identifier]
        except KeyError:
            pass
        else:
            if self.function.result_types is not None:
                Stack().size_to(len(self.function.result_types))

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)

        parameters: list[FixedNumber] = []
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)
            parameters.append(stack.pop())
        self.function.evaluate(stack, local_variables, global_variables, *parameters)

    def __str__(self):
        return f'{super().__str__()}({self.function_identifier})'


class CallIndirectExpression(CallExpression):
    function_type: ExpressionType = None
    call_index: Evaluation = None
    table: list[FunctionExpression] = None

    def __init__(self, **kwargs) -> None:
        if not isinstance(self.children[0], TypeExpression):
            EmptyOperandError.try_raise(2, Stack())
        self.type_expression: TypeExpression = self.children[0]
        if not isinstance(self.children[-1], Evaluation):
            EmptyOperandError.try_raise(1, Stack())
        self.call_index = self.children[-1]
        self.children = self.children[:-1]
        self.children = self.children[1:]
        self.table = FunctionRegistry().functions.copy()

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        self.call_index.evaluate(stack, local_variables)
        index: int = stack.pop().value
        if index >= len(self.table):
            raise UndefinedElementError(f'Index {index} is out of bounds')
        function: FunctionExpression = self.table[index]
        parameters: list[FixedNumber] = []
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)
            parameters.append(stack.pop())
        function.evaluate(stack, local_variables, global_variables, *parameters)

class ReturnExpression(UnaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport:
        if len(self.children) == 1:
            evaluation: FixedNumber = self.check_and_evaluate(stack, local_variables)
            stack.push(evaluation)
        elif len(self.children) > 1:
            for child in self.children:
                child.evaluate(stack, local_variables)
        return EvaluationReport(signal_return=True)

    def __init__(self, **kwargs) -> None:
        pass


class TableFunctionExpression(Evaluation):

    def __init__(self, **kwargs) -> None:
        super().__init__()
        if len(self.children) != 1:
            EmptyOperandError.try_raise(1, Stack())
        if not isinstance(self.children[0], ElementExpression):
            raise TypeError("Function name must be an element expression")
        self.evaluate(Stack(), None)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        if len(self.children) != 1:
            EmptyOperandError.try_raise(1, Stack())
        FunctionRegistry().register_function(self.children[0].element)


class ElementExpression(Evaluation):

    element: Evaluation = None

    def __init__(self, variables=None) -> None:
        super().__init__(variables=variables)
        self.element = variables[self.name]

class ExpressionType(Enum):
    FUNCTION = 0


class TypeExpression(UnaryEvaluation):
    type_name: str | int = None
    expression_type: ExpressionType = None
    parameters: list[NumberVariable] = []
    results: list[NumberType] = []

    def __init__(self, variables=None) -> None:
        super().__init__(numeric=False, skip_operand_check=True)
        Stack().contract(1)
        self.expression_name, self.type_name = self.expression_name.split(' ')
        if len(self.children) != 1:
            operand = variables[self.type_name]
            self.parameters = operand.parameters
            self.results = operand.results
        elif isinstance(operand := self.operand, FunctionExpression):
            self.expression_type = ExpressionType.FUNCTION
            function: FunctionExpression = operand
            self.parameters = function.parameters
            self.results = function.result_types
            variables[self.type_name] = self
        variables['~typing~'] = False

    def __str__(self):
        return f'{super().__str__()}({self.type_name})'


EXPORTED_FUNCTIONS: dict[str, FunctionExpression] = {}
