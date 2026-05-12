"""secure tool code generation and validation"""
import ast
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    name: str
    type: str = "str"
    required: bool = True
    description: str = ""
    default: Optional[Any] = None


class HelperMethod(BaseModel):
    name: str
    parameters: List[ToolParameter] = []
    body: str
    is_async: bool = False
    docstring: str = ""


class GlobalVariable(BaseModel):
    name: str
    type_hint: Optional[str] = None
    value: str


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter] = []
    execute_body: str
    pre_process_body: Optional[str] = None
    post_process_body: Optional[str] = None
    helper_methods: List[HelperMethod] = []
    global_variables: List[GlobalVariable] = []
    timeout: Optional[int] = None
    retries: Optional[int] = None
    retry_delay: Optional[float] = None
    is_async: bool = False


ALLOWED_IMPORTS = {
    "json", "re", "datetime", "typing", "time", "math", "uuid",
    "optorch.tools.decorators", "optorch.state", "optorch.tools.base"
}

BLOCKED_NAMES = {
    "eval", "exec", "__import__", "compile", "globals", "locals",
    "open", "file", "input", "raw_input"
}

ALLOWED_FILE_MODULES = {"tempfile", "pathlib"}


class ToolSecurityError(Exception):
    pass


def validate_code_security(code: str) -> None:
    """ast validation - blocks dangerous operations"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ToolSecurityError(f"syntax error: {e}")
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ToolSecurityError(f"blocked operation: {node.id}")
        
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = [alias.name for alias in node.names]
            
            for name in names:
                full_name = f"{module}.{name}" if module else name
                base_module = full_name.split('.')[0]
                
                if base_module not in ALLOWED_IMPORTS and base_module not in ALLOWED_FILE_MODULES:
                    raise ToolSecurityError(f"import not allowed: {full_name}")


def generate_tool_code(definition: ToolDefinition) -> str:
    """generate complete tool file from definition"""
    
    validate_code_security(definition.execute_body)
    if definition.pre_process_body:
        validate_code_security(definition.pre_process_body)
    if definition.post_process_body:
        validate_code_security(definition.post_process_body)
    for helper in definition.helper_methods:
        validate_code_security(helper.body)
    
    param_hints = []
    for param in definition.parameters:
        type_map = {
            "str": "str",
            "int": "int", 
            "float": "float",
            "bool": "bool",
            "list": "List[Any]",
            "dict": "Dict[str, Any]",
            "Any": "Any"
        }
        hint = type_map.get(param.type, "Any")
        
        if param.required:
            param_hints.append(f"{param.name}: {hint}")
        else:
            default_val = repr(param.default) if param.default is not None else "None"
            param_hints.append(f"{param.name}: {hint} = {default_val}")
    
    params_str = ", ".join(param_hints) if param_hints else ""
    
    schema_properties = {}
    required_params = []
    for param in definition.parameters:
        prop = {"type": param.type, "description": param.description}
        schema_properties[param.name] = prop
        if param.required:
            required_params.append(param.name)
    
    code_lines = [
        '"""',
        definition.description,
        '"""',
        "from typing import Any, Dict, List, Optional",
        "from optorch.tools.decorators import tool",
        "",
        "",
    ]
    
    for global_var in definition.global_variables:
        if global_var.type_hint:
            code_lines.append(f"{global_var.name}: {global_var.type_hint} = {global_var.value}")
        else:
            code_lines.append(f"{global_var.name} = {global_var.value}")
    
    if definition.global_variables:
        code_lines.append("")
    
    for helper in definition.helper_methods:
        helper_params = []
        for param in helper.parameters:
            type_map = {
                "str": "str", "int": "int", "float": "float", "bool": "bool",
                "list": "List[Any]", "dict": "Dict[str, Any]", "Any": "Any"
            }
            hint = type_map.get(param.type, "Any")
            if param.required:
                helper_params.append(f"{param.name}: {hint}")
            else:
                default_val = repr(param.default) if param.default is not None else "None"
                helper_params.append(f"{param.name}: {hint} = {default_val}")
        
        params_str = ", ".join(helper_params) if helper_params else ""
        async_prefix = "async " if helper.is_async else ""
        
        code_lines.append(f"{async_prefix}def {helper.name}({params_str}):")
        if helper.docstring:
            code_lines.append(f'    """{helper.docstring}"""')
        
        for line in helper.body.split('\n'):
            code_lines.append(f"    {line}" if line.strip() else "")
        
        code_lines.append("")
        code_lines.append("")
    
    decorator_args = []
    if definition.timeout:
        decorator_args.append(f"timeout={definition.timeout}")
    if definition.retries:
        decorator_args.append(f"retries={definition.retries}")
    if definition.retry_delay:
        decorator_args.append(f"retry_delay={definition.retry_delay}")
    
    decorator = f"@tool({', '.join(decorator_args)})" if decorator_args else "@tool"
    code_lines.append(decorator)
    async_prefix = "async " if definition.is_async else ""
    code_lines.append(f"{async_prefix}def {definition.name}({params_str}):")
    code_lines.append(f'    """{definition.description}')
    
    for param in definition.parameters:
        code_lines.append(f"    ")
        code_lines.append(f"    Args:")
        code_lines.append(f"        {param.name}: {param.description}")
    
    code_lines.append('    """')
    
    if definition.pre_process_body:
        code_lines.append("    # pre-process")
        for line in definition.pre_process_body.split('\n'):
            code_lines.append(f"    {line}" if line.strip() else "")
        code_lines.append("")
    
    for line in definition.execute_body.split('\n'):
        code_lines.append(f"    {line}" if line.strip() else "")
    
    if definition.post_process_body:
        code_lines.append("")
        code_lines.append("    # post-process")
        for line in definition.post_process_body.split('\n'):
            code_lines.append(f"    {line}" if line.strip() else "")
    
    return '\n'.join(code_lines)
