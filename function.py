from __future__ import annotations

from enum import Enum

from custom_exceptions import InvalidFunctionSignatureError, UnknownFunctionError, EmptyOperandError
from enums import NumberType
from evaluations import Evaluation, UnaryEvaluation, EvaluationReport
from expressions import ExportExpression, SExpression
from operations import ParamExpression, ResultExpression
from variables import VariableWatch, FixedNumber, NumberVariable, Stack


class FunctionExpression(Evaluation):
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

    def __init__(self, _=None) -> None:
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
            self.parameters.append(NumberVariable(parameter_expression.number_type, parameter_expression.name))
            child_index += 1
        # Remove parameters from children
        self.children = self.children[child_index:]
        if len(self.children) > 0:
            if isinstance(self.children[0], ResultExpression):
                result_expression: ResultExpression = self.children[0]
                self.result_type = result_expression.number_type
                self.children = self.children[1:]
        for child in self.children:
            if not isinstance(child, Evaluation):
                # raise TypeError("Expression can not be evaluated")
                pass

    def initialize_parameters(self, local_variables: VariableWatch,
                              *args: NumberVariable | FixedNumber) \
            -> VariableWatch:
        # Check parameters
        if len(args) != len(self.parameters):
            raise InvalidFunctionSignatureError(self, *args)
        for index, arg in enumerate(args):
            if self.parameters[index].number_type != arg.number_type:
                raise TypeError("Invalid parameter type")
            local_variables.add_variable(arg, self.parameters[index].name)
        for expression in self.children:
            if not isinstance(expression, Evaluation):
                raise TypeError("Expression can not be evaluated")
        return local_variables

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> NumberType:
        # Check parameters
        # local_variables = self.initialize_parameters(local_variables, *args)
        for evaluation in self.children:
            evaluation.assert_correctness(local_variables)

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)
        # Check parameters
        local_variables = self.initialize_parameters(local_variables, *args)
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)


class InvokeExpression(Evaluation):
    function: FunctionExpression = None

    def __init__(self, _=None) -> None:
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
        self.function.evaluate(stack, local_variables)

    def __str__(self):
        return f'{super().__str__()}({self.function.export_as})'


class CallExpression(Evaluation):
    function_identifier: int | str = None

    def __init__(self) -> None:
        super().__init__()
        self.expression_name, self.function_identifier = self.expression_name.split(' ')

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)

        function: FunctionExpression = local_variables[self.function_identifier]

        parameters: list[FixedNumber] = []
        for evaluation in self.children:
            evaluation.evaluate(stack, local_variables)
            parameters.append(stack.pop())
        function.evaluate(stack, local_variables)

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> NumberType:
        for child in self.children:
            child.assert_correctness(local_variables)

    def __str__(self):
        return f'{super().__str__()}({self.function_identifier})'


class CallIndirectExpression(CallExpression):
    function_type: ExpressionType = None
    function_identifier: Evaluation = None

    def __init__(self) -> None:
        if not isinstance(self.children[0], TypeExpression):
            raise EmptyOperandError(2)
        self.type_expression: TypeExpression = self.children[0]
        self.children = self.children[1:]
        if not isinstance(self.children[0], Evaluation):
            raise EmptyOperandError(2)
        self.function_identifier = self.children[0]
        self.children = self.children[1:]

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        pass  # TODO

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> NumberType:
        self.function_identifier.assert_correctness(local_variables)
        for child in self.children:
            child.assert_correctness(local_variables)


class ReturnExpression(UnaryEvaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> EvaluationReport:
        evaluation: FixedNumber = self.check_and_evaluate(stack, local_variables)
        stack.push(evaluation)
        return EvaluationReport(signal_return=True)

    def __init__(self) -> None:
        pass


class TableFunctionExpression(Evaluation):

    def evaluate(self, stack: Stack, local_variables: VariableWatch = None, global_variables=None) -> None:
        super().evaluate(stack, local_variables)

    def assert_correctness(self, local_variables: VariableWatch, global_variables=None) -> None:
        if len(self.children) != 1:
            raise EmptyOperandError(1)


class ExpressionType(Enum):
    FUNCTION = 0


class TypeExpression(UnaryEvaluation):
    type_name: str | int = None
    expression_type: ExpressionType = None

    def __init__(self) -> None:
        super().__init__(numeric=False)
        self.expression_name, self.type_name = self.expression_name.split(' ')
        if len(self.children) != 1:
            return
        if isinstance(self.operand, FunctionExpression):
            self.expression_type = ExpressionType.FUNCTION

    def __str__(self):
        return f'{super().__str__()}({self.type_name})'


EXPORTED_FUNCTIONS: dict[str, FunctionExpression] = {}
