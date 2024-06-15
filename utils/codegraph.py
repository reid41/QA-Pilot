import ast 
import os

def parse_python_code(filepath):
    """Parse Python code file, extract classes, methods, global functions, imported modules and their source code, and the call relationships."""
    with open(filepath, 'r', encoding='utf-8') as file:
        source = file.read()
    node = ast.parse(source)

    classes = []
    methods = []
    functions = []
    imports = []
    links = []
    method_calls = {}
    function_calls = {}
    import_calls = {}
    class_inheritance = {}

    # Extract classes and methods
    for item in ast.walk(node):
        if isinstance(item, ast.ClassDef):
            class_start_line = item.lineno - 1
            class_end_line = item.end_lineno
            class_source = "\n".join(source.splitlines()[class_start_line:class_end_line])
            classes.append({'key': item.name, 'name': item.name, 'class': 'class', 'color': 'lightblue', 'source': class_source})

            for base in item.bases:
                if isinstance(base, ast.Name):
                    class_inheritance[item.name] = base.id

            for method in [n for n in item.body if isinstance(n, ast.FunctionDef)]:
                method_start_line = method.lineno - 1
                method_end_line = method.end_lineno
                method_source = "\n".join(source.splitlines()[method_start_line:method_end_line])
                methods.append({'key': f"{item.name}.{method.name}", 'name': method.name, 'class': 'method', 'color': 'lightgreen', 'source': method_source})
                links.append({'from': item.name, 'to': f"{item.name}.{method.name}", 'color': 'blue'})

                method_calls[f"{item.name}.{method.name}"] = []
                for stmt in ast.walk(method):
                    if isinstance(stmt, ast.Call):
                        if isinstance(stmt.func, ast.Name):
                            method_calls[f"{item.name}.{method.name}"].append(stmt.func.id)
                        elif isinstance(stmt.func, ast.Attribute):
                            method_calls[f"{item.name}.{method.name}"].append(stmt.func.attr)

    # Handle inheritance relationships
    for child, parent in class_inheritance.items():
        links.append({'from': child, 'to': parent, 'category': 'dashed', 'color': 'gray'})

    # Extract global functions
    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            function_start_line = item.lineno - 1
            function_end_line = item.end_lineno
            function_source = "\n".join(source.splitlines()[function_start_line:function_end_line])
            functions.append({'key': item.name, 'name': item.name, 'class': 'function', 'color': 'lightcoral', 'source': function_source})

            function_calls[item.name] = []
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.Call):
                    if isinstance(stmt.func, ast.Name):
                        function_calls[item.name].append(stmt.func.id)
                    elif isinstance(stmt.func, ast.Attribute):
                        function_calls[item.name].append(stmt.func.attr)

    # Extract imported modules, classes, functions, or variables
    for item in node.body:
        if isinstance(item, ast.Import):
            for alias in item.names:
                imports.append({'key': alias.name, 'name': alias.name, 'class': 'import', 'color': 'lightyellow', 'source': f"import {alias.name}"})
        elif isinstance(item, ast.ImportFrom):
            module = item.module
            for alias in item.names:
                import_name = f"{module}.{alias.name}"
                imports.append({'key': alias.name, 'name': alias.name, 'class': 'import', 'color': 'lightyellow', 'source': f"from {module} import {alias.name}"})
                import_calls[alias.name] = import_name

    # Check which imports are actually called
    used_imports = set()
    for calls in method_calls.values():
        used_imports.update(calls)
    for calls in function_calls.values():
        used_imports.update(calls)

    # Filter out unused imports
    imports = [imp for imp in imports if imp['key'] in used_imports]

    # Add method and global function call links
    for caller, callees in method_calls.items():
        for callee in callees:
            if callee in method_calls or callee in function_calls or callee in import_calls:
                links.append({'from': caller, 'to': callee, 'category': 'dashed', 'color': 'green'})

    for caller, callees in function_calls.items():
        for callee in callees:
            if callee in method_calls or callee in function_calls or callee in import_calls:
                links.append({'from': caller, 'to': callee, 'category': 'dashed', 'color': 'green'})

    for import_name, import_module in import_calls.items():
        if import_name in used_imports:
            for caller, callees in method_calls.items():
                if import_name in callees:
                    links.append({'from': caller, 'to': import_name, 'category': 'dashed', 'color': 'orange'})
            for caller, callees in function_calls.items():
                if import_name in callees:
                    links.append({'from': caller, 'to': import_name, 'category': 'dashed', 'color': 'orange'})

    return {'nodeDataArray': classes + methods + functions + imports, 'linkDataArray': links}

def read_current_repo_path(current_session):
    if current_session:
        print("=============> path: ", os.path.join("projects", current_session['name']))
        return os.path.join("projects", current_session['name'])
    return None

def build_file_tree(directory):
    """Build the file tree for the given directory"""
    file_tree = []
    for root, dirs, files in os.walk(directory):
        for d in dirs:
            dir_path = os.path.join(root, d)
            file_tree.append({
                'name': d,
                'path': dir_path,
                'type': 'directory',
                'children': build_file_tree(dir_path)
            })
        for f in files:
            if f.endswith('.py'):
                file_path = os.path.join(root, f)
                file_tree.append({
                    'name': f,
                    'path': file_path,
                    'type': 'file'
                })
        break  # Only traverse current directory, not recursively
    return file_tree