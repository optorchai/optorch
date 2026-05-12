"""parse existing tool code back into structured format"""
import ast
from typing import Optional
from .tool_builder import ToolDefinition, ToolParameter, HelperMethod, GlobalVariable


def parse_tool_file(code: str, expected_name: Optional[str] = None) -> Optional[ToolDefinition]:
    """attempt to parse tool code back into structured definition
    
    returns None if code doesn't follow expected pattern
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    
    all_functions = []
    global_assignments = []
    
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_functions.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            global_assignments.append(node)
    
    func_def = None
    decorator_args = {}
    
    for node in all_functions:
        has_tool_decorator = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                has_tool_decorator = True
                break
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'tool':
                    has_tool_decorator = True
                    for keyword in decorator.keywords:
                        if isinstance(keyword.value, ast.Constant):
                            decorator_args[keyword.arg] = keyword.value.value
                    break
        
        if has_tool_decorator:
            if expected_name is None or node.name == expected_name:
                func_def = node
                break
    
    if not func_def:
        return None
    
    name = func_def.name
    is_async = isinstance(func_def, ast.AsyncFunctionDef)
    description = ast.get_docstring(func_def) or ""
    
    parameters = []
    for arg in func_def.args.args:
        if arg.arg == 'self':
            continue
        
        param_type = "Any"
        if arg.annotation:
            param_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else "Any"
        
        type_map = {
            "str": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "list": "list",
            "dict": "dict",
            "List[Any]": "list",
            "Dict[str, Any]": "dict"
        }

        param_type = type_map.get(param_type, "Any")
        required = True
        default = None
        num_defaults = len(func_def.args.defaults)
        num_args = len(func_def.args.args)
        arg_idx = func_def.args.args.index(arg)
        default_idx = arg_idx - (num_args - num_defaults)
        
        if default_idx >= 0:
            required = False
            default_node = func_def.args.defaults[default_idx]
            if isinstance(default_node, ast.Constant):
                default = default_node.value
        
        parameters.append(ToolParameter(
            name=arg.arg,
            type=param_type,
            required=required,
            description="",
            default=default
        ))

    body_lines = []
    for stmt in func_def.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue
        if hasattr(ast, 'unparse'):
            body_lines.append(ast.unparse(stmt))
    
    execute_body = '\n'.join(body_lines) if body_lines else "pass"
    
    helper_methods = []
    for helper_func in all_functions:
        if helper_func == func_def:
            continue
        
        helper_name = helper_func.name
        helper_is_async = isinstance(helper_func, ast.AsyncFunctionDef)
        helper_docstring = ast.get_docstring(helper_func) or ""
        
        helper_params = []
        for arg in helper_func.args.args:
            if arg.arg == 'self':
                continue
            
            param_type = "Any"
            if arg.annotation:
                param_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else "Any"
            
            type_map = {
                "str": "str",
                "int": "int",
                "float": "float",
                "bool": "bool",
                "list": "list",
                "dict": "dict",
                "List[Any]": "list",
                "Dict[str, Any]": "dict",
                "Optional[str]": "str",
                "Optional[Dict[str, Any]]": "dict",
            }
            param_type = type_map.get(param_type, "Any")
            required = True
            default = None
            num_defaults = len(helper_func.args.defaults)
            num_args = len(helper_func.args.args)
            arg_idx = helper_func.args.args.index(arg)
            default_idx = arg_idx - (num_args - num_defaults)
            
            if default_idx >= 0:
                required = False
                default_node = helper_func.args.defaults[default_idx]
                if isinstance(default_node, ast.Constant):
                    default = default_node.value
            
            helper_params.append(ToolParameter(
                name=arg.arg,
                type=param_type,
                required=required,
                description="",
                default=default
            ))
        
        helper_body_lines = []
        for stmt in helper_func.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                continue
            if hasattr(ast, 'unparse'):
                helper_body_lines.append(ast.unparse(stmt))
        
        helper_body = '\n'.join(helper_body_lines) if helper_body_lines else "pass"
        
        helper_methods.append(HelperMethod(
            name=helper_name,
            parameters=helper_params,
            body=helper_body,
            is_async=helper_is_async,
            docstring=helper_docstring
        ))
    
    global_variables = []
    for assign_node in global_assignments:
        if isinstance(assign_node, ast.AnnAssign):
            if isinstance(assign_node.target, ast.Name):
                var_name = assign_node.target.id
                type_hint = ast.unparse(assign_node.annotation) if hasattr(ast, 'unparse') and assign_node.annotation else None
                value = ast.unparse(assign_node.value) if hasattr(ast, 'unparse') and assign_node.value else "None"
                global_variables.append(GlobalVariable(
                    name=var_name,
                    type_hint=type_hint,
                    value=value
                ))
        elif isinstance(assign_node, ast.Assign):
            for target in assign_node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    value = ast.unparse(assign_node.value) if hasattr(ast, 'unparse') else "None"
                    global_variables.append(GlobalVariable(
                        name=var_name,
                        type_hint=None,
                        value=value
                    ))
    
    return ToolDefinition(
        name=name,
        description=description.split('\n')[0] if description else "",
        parameters=parameters,
        execute_body=execute_body,
        timeout=decorator_args.get('timeout'),
        retries=decorator_args.get('retries'),
        retry_delay=decorator_args.get('retry_delay'),
        is_async=is_async,
        helper_methods=helper_methods,
        global_variables=global_variables
    )
