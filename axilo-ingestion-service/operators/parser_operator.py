import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from tree_sitter import Language, Parser
import tree_sitter_python as tspython

class ParserOperator:
    """Handles parsing source code files using Tree-sitter"""
    
    # Python built-in functions
    PYTHON_BUILTINS = {
        'print', 'len', 'range', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 
        'tuple', 'open', 'input', 'enumerate', 'zip', 'map', 'filter', 'sum', 'max', 
        'min', 'abs', 'all', 'any', 'isinstance', 'type', 'dir', 'help', 'sorted', 
        'reversed', 'next', 'iter', 'hash', 'id', 'getattr', 'setattr', 'hasattr',
        'callable', 'super', 'property', 'staticmethod', 'classmethod'
    }
    
    def __init__(self, metadata_base_dir: str = '/tmp/metadata', compression_level: int = 1, output_format: str = 'md'):
        self.metadata_base_dir = metadata_base_dir
        self.compression_level = compression_level
        self.output_format = output_format  # 'json' or 'md'
        self.python_language = Language(tspython.language(), 'python')
        self.parser = Parser()
        self.parser.set_language(self.python_language)
        
    def parse_python_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse a Python file and extract metadata
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary containing extracted metadata
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            tree = self.parser.parse(source_code)
            root_node = tree.root_node
            
            # Extract calls for functions and methods
            imports_data = self._extract_imports(root_node, source_code)
            
            # Build lookup registries first
            import_registry = self._build_import_registry(imports_data)
            
            # Extract classes and functions WITH calls
            classes_data = self._extract_classes_with_calls(root_node, source_code, import_registry)
            functions_data = self._extract_functions_with_calls(root_node, source_code, import_registry, classes_data)
            
            # Compress imports based on compression level
            if self.compression_level >= 1:
                imports_data = self._compress_imports(imports_data)
            
            metadata = {
                'file_path': file_path,
                'imports': imports_data,
                'classes': classes_data,
                'functions': functions_data,
            }
            
            # Only include comments if compression_level is 0 (full)
            if self.compression_level == 0:
                metadata['comments'] = self._extract_comments(root_node, source_code)
            
            return metadata
            
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_import_registry(self, imports: List[Dict]) -> Dict[str, Dict]:
        """Build a registry of imported modules and functions"""
        registry = {}
        
        for imp in imports:
            import_text = imp['module']
            
            # Handle 'import module' or 'import module as alias'
            if imp['type'] == 'import':
                parts = import_text.replace('import ', '').split(' as ')
                module_name = parts[0].strip()
                alias = parts[1].strip() if len(parts) > 1 else module_name
                
                registry[alias] = {
                    'module': module_name,
                    'type': 'external',  # Will refine later with project detection
                    'import_type': 'module'
                }
            
            # Handle 'from module import name' or 'from module import name as alias'
            elif imp['type'] == 'from_import':
                # Parse: from X import Y, Z as W
                if ' import ' in import_text:
                    parts = import_text.split(' import ')
                    module_name = parts[0].replace('from ', '').strip()
                    imports_part = parts[1].strip()
                    
                    # Handle multiple imports
                    for item in imports_part.split(','):
                        item = item.strip()
                        if ' as ' in item:
                            name, alias = item.split(' as ')
                            name = name.strip()
                            alias = alias.strip()
                        else:
                            name = alias = item
                        
                        registry[alias] = {
                            'module': module_name,
                            'name': name,
                            'type': 'external',
                            'import_type': 'from'
                        }
        
        return registry
    
    def _compress_imports(self, imports: List[Dict]) -> Dict[str, List[str]]:
        """
        Compress imports from verbose list format to compact dict format
        
        From: [{"type": "from_import", "module": "from typing import Dict, List", "line": 4}]
        To: {"typing": ["Dict", "List"], "re": ["*"]}
        """
        compressed = {}
        
        for imp in imports:
            import_text = imp['module']
            
            if imp['type'] == 'import':
                # Handle 'import module' or 'import module as alias'
                parts = import_text.replace('import ', '').split(' as ')
                module_name = parts[0].strip()
                
                # Split multiple imports like "import os, sys"
                for mod in module_name.split(','):
                    mod = mod.strip()
                    if mod not in compressed:
                        compressed[mod] = ['*']
            
            elif imp['type'] == 'from_import':
                # Handle 'from module import name1, name2'
                if ' import ' in import_text:
                    parts = import_text.split(' import ')
                    module_name = parts[0].replace('from ', '').strip()
                    imports_part = parts[1].strip()
                    
                    # Handle multi-line imports by removing newlines
                    imports_part = imports_part.replace('\n', ' ').replace('(', '').replace(')', '')
                    
                    if module_name not in compressed:
                        compressed[module_name] = []
                    
                    # Parse imported items
                    for item in imports_part.split(','):
                        item = item.strip()
                        if not item:
                            continue
                        
                        # Handle 'name as alias' - just keep the original name
                        if ' as ' in item:
                            name = item.split(' as ')[0].strip()
                        else:
                            name = item
                        
                        if name and name not in compressed[module_name]:
                            compressed[module_name].append(name)
        
        return compressed
    
    def _build_local_registry(self, classes: List[Dict], functions: List[Dict]) -> Set[str]:
        """Build a set of locally defined functions and classes"""
        local_names = set()
        
        # Add function names
        for func in functions:
            if func.get('name'):
                local_names.add(func['name'])
        
        # Add class names and their methods
        for cls in classes:
            if cls.get('name'):
                local_names.add(cls['name'])
                for method in cls.get('methods', []):
                    if method.get('name'):
                        local_names.add(method['name'])
        
        return local_names
    
    def _extract_imports(self, node, source_code: bytes) -> List[Dict]:
        """Extract import statements"""
        imports = []
        
        def traverse(n):
            if n.type == 'import_statement':
                imports.append({
                    'type': 'import',
                    'module': source_code[n.start_byte:n.end_byte].decode('utf-8'),
                    'line': n.start_point[0] + 1
                })
            elif n.type == 'import_from_statement':
                imports.append({
                    'type': 'from_import',
                    'module': source_code[n.start_byte:n.end_byte].decode('utf-8'),
                    'line': n.start_point[0] + 1
                })
            
            for child in n.children:
                traverse(child)
        
        traverse(node)
        return imports
    
    def _extract_classes_with_calls(self, node, source_code: bytes, import_registry: Dict) -> List[Dict]:
        """Extract class definitions with method calls"""
        classes = []
        
        def traverse(n):
            if n.type == 'class_definition':
                class_info = {
                    'name': None,
                    'methods': [],
                    'docstring': None,
                    'bases': []
                }
                
                # Include line numbers only if compression_level is 0
                if self.compression_level == 0:
                    class_info['line_start'] = n.start_point[0] + 1
                    class_info['line_end'] = n.end_point[0] + 1
                
                for child in n.children:
                    if child.type == 'identifier':
                        class_info['name'] = source_code[child.start_byte:child.end_byte].decode('utf-8')
                    elif child.type == 'argument_list':
                        # Extract base classes
                        for arg in child.children:
                            if arg.type == 'identifier':
                                class_info['bases'].append(
                                    source_code[arg.start_byte:arg.end_byte].decode('utf-8')
                                )
                    elif child.type == 'block':
                        # Extract methods and docstring
                        class_info['docstring'] = self._extract_docstring(child, source_code)
                
                classes.append(class_info)
            
            for child in n.children:
                traverse(child)
        
        traverse(node)
        return classes
    
    def _extract_functions_with_calls(self, node, source_code: bytes, import_registry: Dict, classes_data: List[Dict]) -> List[Dict]:
        """Extract top-level function definitions with calls"""
        functions = []
        
        # Build local registry from classes and functions we're extracting
        local_registry = set()
        for cls in classes_data:
            if cls.get('name'):
                local_registry.add(cls['name'])
        
        # Only get direct children functions (not methods inside classes)
        # Need to handle both direct function_definition and decorated_definition nodes
        for child in node.children:
            if child.type == 'function_definition':
                func_info = self._parse_function_with_calls(child, source_code, import_registry, local_registry)
                if func_info:
                    # Add function name to local registry for subsequent functions
                    if func_info.get('name'):
                        local_registry.add(func_info['name'])
                    functions.append(func_info)
            elif child.type == 'decorated_definition':
                # Handle decorated functions
                for decorated_child in child.children:
                    if decorated_child.type == 'function_definition':
                        func_info = self._parse_function_with_calls(decorated_child, source_code, import_registry, local_registry)
                        if func_info:
                            # Extract decorators from the decorated_definition node
                            decorators = []
                            for dec_child in child.children:
                                if dec_child.type == 'decorator':
                                    decorator_text = source_code[dec_child.start_byte:dec_child.end_byte].decode('utf-8')
                                    decorators.append(decorator_text)
                            func_info['decorators'] = decorators
                            
                            # Add function name to local registry for subsequent functions
                            if func_info.get('name'):
                                local_registry.add(func_info['name'])
                            functions.append(func_info)
        
        # Now extract methods from classes
        for cls in classes_data:
            cls['methods'] = self._extract_methods_with_calls(node, cls['name'], source_code, import_registry, local_registry)
        
        return functions
    
    def _extract_methods_with_calls(self, root_node, class_name: str, source_code: bytes, import_registry: Dict, local_registry: Set[str]) -> List[Dict]:
        """Extract methods from a class with calls"""
        methods = []
        
        # Find the class node
        def find_class(node):
            if node.type == 'class_definition':
                for child in node.children:
                    if child.type == 'identifier':
                        name = source_code[child.start_byte:child.end_byte].decode('utf-8')
                        if name == class_name:
                            return node
            elif node.type == 'decorated_definition':
                # Check if this is a decorated class
                for child in node.children:
                    if child.type == 'class_definition':
                        result = find_class(child)
                        if result:
                            return result
            
            for child in node.children:
                result = find_class(child)
                if result:
                    return result
            return None
        
        class_node = find_class(root_node)
        if not class_node:
            return methods
        
        # Find the block containing methods
        for child in class_node.children:
            if child.type == 'block':
                for block_child in child.children:
                    if block_child.type == 'function_definition':
                        method_info = self._parse_function_with_calls(block_child, source_code, import_registry, local_registry)
                        if method_info:
                            methods.append(method_info)
                    elif block_child.type == 'decorated_definition':
                        # Handle decorated methods
                        for decorated_child in block_child.children:
                            if decorated_child.type == 'function_definition':
                                method_info = self._parse_function_with_calls(decorated_child, source_code, import_registry, local_registry)
                                if method_info:
                                    # Extract decorators from the decorated_definition node
                                    decorators = []
                                    for dec_child in block_child.children:
                                        if dec_child.type == 'decorator':
                                            decorator_text = source_code[dec_child.start_byte:dec_child.end_byte].decode('utf-8')
                                            decorators.append(decorator_text)
                                    method_info['decorators'] = decorators
                                    methods.append(method_info)
        
        return methods
    
    def _parse_function_with_calls(self, func_node, source_code: bytes, import_registry: Dict, local_registry: Set[str]) -> Optional[Dict]:
        """Parse a function/method node with call extraction"""
        func_info = {
            'name': None,
            'parameters': [],
            'return_type': None,
            'returns': [],
            'docstring': None,
            'decorators': [],  # Will be set by caller if in decorated_definition
            'calls': []
        }
        
        # Include line numbers only if compression_level is 0
        if self.compression_level == 0:
            func_info['line_start'] = func_node.start_point[0] + 1
            func_info['line_end'] = func_node.end_point[0] + 1
        
        for child in func_node.children:
            if child.type == 'identifier':
                func_info['name'] = source_code[child.start_byte:child.end_byte].decode('utf-8')
            elif child.type == 'parameters':
                func_info['parameters'] = self._extract_parameters(child, source_code)
            elif child.type == 'type':
                # Extract return type annotation (e.g., -> int, -> List[str])
                func_info['return_type'] = source_code[child.start_byte:child.end_byte].decode('utf-8')
            elif child.type == 'block':
                func_info['docstring'] = self._extract_docstring(child, source_code)
                # Extract calls from the function body
                func_info['calls'] = self._extract_calls_from_node(child, source_code, import_registry, local_registry)
                # Extract return statements
                func_info['returns'] = self._extract_return_statements(child, source_code)
        
        # Clean up empty/null values for compression level >= 1
        if self.compression_level >= 1:
            func_info = self._remove_empty_values(func_info)
        
        return func_info
    
    def _extract_parameters(self, params_node, source_code: bytes) -> List[str]:
        """Extract function parameters"""
        parameters = []
        
        for child in params_node.children:
            if child.type in ['identifier', 'typed_parameter', 'default_parameter', 
                             'typed_default_parameter', 'list_splat_pattern', 'dictionary_splat_pattern']:
                param_text = source_code[child.start_byte:child.end_byte].decode('utf-8')
                parameters.append(param_text)
        
        return parameters
    
    def _extract_docstring(self, block_node, source_code: bytes) -> Optional[str]:
        """Extract docstring from a block"""
        for child in block_node.children:
            if child.type == 'expression_statement':
                for expr_child in child.children:
                    if expr_child.type == 'string':
                        docstring = source_code[expr_child.start_byte:expr_child.end_byte].decode('utf-8')
                        # Remove quotes
                        docstring = docstring.strip('"""').strip("'''").strip('"').strip("'")
                        return docstring.strip()
        return None
    
    def _extract_return_statements(self, block_node, source_code: bytes) -> List[Dict]:
        """Extract return statements from a function block"""
        returns = []
        
        def traverse(node):
            if node.type == 'return_statement':
                return_info = {}
                
                # Include line numbers only if compression_level is 0
                if self.compression_level == 0:
                    return_info['line'] = node.start_point[0] + 1
                
                # Extract the return value
                for child in node.children:
                    if child.type not in ['return', 'comment']:
                        # Get the returned expression
                        return_value = source_code[child.start_byte:child.end_byte].decode('utf-8')
                        return_info['value'] = return_value
                        break
                
                if return_info:  # Only add if there's actual data
                    returns.append(return_info)
            
            # Traverse children
            for child in node.children:
                traverse(child)
        
        traverse(block_node)
        return returns
    
    def _remove_empty_values(self, data: Dict) -> Dict:
        """Remove null, empty lists, and empty strings from dictionary"""
        return {
            k: v for k, v in data.items()
            if v is not None and v != [] and v != '' and v != {}
        }
    
    def _extract_comments(self, node, source_code: bytes) -> List[Dict]:
        """Extract comments"""
        comments = []
        
        def traverse(n):
            if n.type == 'comment':
                comments.append({
                    'text': source_code[n.start_byte:n.end_byte].decode('utf-8'),
                    'line': n.start_point[0] + 1
                })
            
            for child in n.children:
                traverse(child)
        
        traverse(node)
        return comments
    
    def _extract_calls_from_node(self, func_node, source_code: bytes,
                                 import_registry: Dict, local_registry: Set[str]) -> List[Dict]:
        """Extract all function calls from a function/method node"""
        calls = []
        
        def traverse(node):
            if node.type == 'call':
                call_info = self._parse_call_node(node, source_code, import_registry, local_registry)
                if call_info:
                    calls.append(call_info)
            
            for child in node.children:
                traverse(child)
        
        traverse(func_node)
        return calls
    
    def _parse_call_node(self, call_node, source_code: bytes,
                        import_registry: Dict, local_registry: Set[str]) -> Optional[Dict]:
        """Parse a call node and categorize it"""
        # Get the function being called
        function_node = call_node.child_by_field_name('function')
        if not function_node:
            return None
        
        call_text = source_code[function_node.start_byte:function_node.end_byte].decode('utf-8')
        
        call_info = {
            'name': call_text,
            'type': 'unknown',
        }
        
        # Include line numbers only if compression_level is 0
        if self.compression_level == 0:
            call_info['line'] = call_node.start_point[0] + 1
        
        # Parse the call (could be: func(), obj.method(), module.func(), etc.)
        parts = call_text.split('.')
        base_name = parts[0]
        
        # Categorize the call
        if len(parts) == 1:
            # Simple function call: func()
            if base_name in self.PYTHON_BUILTINS:
                # Skip built-in functions
                return None
            elif base_name in local_registry:
                call_info['type'] = 'internal'
            elif base_name in import_registry:
                imp_info = import_registry[base_name]
                call_info['type'] = imp_info['type']
                call_info['module'] = imp_info['module']
            else:
                # Skip unknown simple calls (might be variables, etc.)
                return None
        else:
            # Method/attribute call: obj.method() or module.func()
            if base_name in import_registry:
                # This is a module/imported function call
                imp_info = import_registry[base_name]
                call_info['type'] = imp_info['type']
                call_info['module'] = imp_info['module']
            elif base_name in local_registry:
                # Calling a method on a local class/object
                call_info['type'] = 'internal'
            else:
                # Skip method calls on instances (e.g., list.append, dict.get)
                # These are typically instance methods, not relevant for call graph
                return None
        
        # Clean up empty values for compression level >= 1
        if self.compression_level >= 1:
            call_info = self._remove_empty_values(call_info)
        
        return call_info
    
    def create_metadata_file(self, file_path: str, repo_path: str, repo_name: str) -> bool:
        """
        Create metadata file (JSON or MD) for a Python source file
        
        Args:
            file_path: Path to the source file
            repo_path: Root path of the repository
            repo_name: Name of the repository
            
        Returns:
            Success status
        """
        try:
            # Parse the file
            metadata = self.parse_python_file(file_path)
            
            if metadata is None:
                return False
            
            # Calculate relative path
            rel_path = os.path.relpath(file_path, repo_path)
            
            # Create metadata directory structure
            metadata_dir = os.path.join(self.metadata_base_dir, repo_name)
            metadata_file_dir = os.path.join(metadata_dir, os.path.dirname(rel_path))
            
            os.makedirs(metadata_file_dir, exist_ok=True)
            
            # Create metadata file path
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            if self.output_format == 'md':
                metadata_file_name = base_name + '.md'
                metadata_file_path = os.path.join(metadata_file_dir, metadata_file_name)
                
                # Convert to Markdown and save
                markdown_content = self._convert_to_markdown(metadata, rel_path)
                with open(metadata_file_path, 'w') as f:
                    f.write(markdown_content)
            else:
                # Default to JSON
                metadata_file_name = base_name + '.json'
                metadata_file_path = os.path.join(metadata_file_dir, metadata_file_name)
                
                # Save as JSON
                with open(metadata_file_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            print(f"Created metadata: {metadata_file_path}")
            return True
            
        except Exception as e:
            print(f"Error creating metadata for {file_path}: {e}")
            return False
    
    def cleanup_metadata(self, repo_name: str):
        """Clean up metadata directory"""
        metadata_dir = os.path.join(self.metadata_base_dir, repo_name)
        
        if os.path.exists(metadata_dir):
            import shutil
            shutil.rmtree(metadata_dir)
            print(f"Cleaned up metadata directory: {metadata_dir}")
    
    def _convert_to_markdown(self, metadata: Dict, file_path: str) -> str:
        """Convert metadata dictionary to Markdown format"""
        lines = []
        
        # File header
        lines.append(f"# {file_path}\n")
        
        # Imports section
        if metadata.get('imports'):
            lines.append("## Imports\n")
            imports = metadata['imports']
            
            if isinstance(imports, dict):
                # Compressed format
                for module, items in sorted(imports.items()):
                    if items == ['*']:
                        lines.append(f"- `{module}`")
                    else:
                        items_str = ", ".join(items)
                        lines.append(f"- `{module}`: {items_str}")
            else:
                # List format (level 0)
                for imp in imports:
                    lines.append(f"- {imp['module']}")
            
            lines.append("")
        
        # Classes section
        if metadata.get('classes'):
            lines.append("## Classes\n")
            
            for cls in metadata['classes']:
                class_name = cls.get('name', 'Unknown')
                bases = cls.get('bases', [])
                
                if bases:
                    bases_str = f"({', '.join(bases)})"
                    lines.append(f"### {class_name}{bases_str}\n")
                else:
                    lines.append(f"### {class_name}\n")
                
                # Docstring
                if cls.get('docstring'):
                    lines.append(f"*{cls['docstring']}*\n")
                
                # Methods
                if cls.get('methods'):
                    lines.append("**Methods:**\n")
                    for method in cls['methods']:
                        method_sig = self._format_function_signature(method)
                        lines.append(f"- `{method_sig}`")
                        
                        # Method calls
                        if method.get('calls'):
                            calls_str = ", ".join([c['name'] for c in method['calls']])
                            lines.append(f"  - Calls: {calls_str}")
                        
                        # Method returns
                        if method.get('returns'):
                            returns_str = ", ".join([r.get('value', '') for r in method['returns'] if r.get('value')])
                            if returns_str:
                                lines.append(f"  - Returns: {returns_str}")
                    
                    lines.append("")
        
        # Functions section
        if metadata.get('functions'):
            lines.append("## Functions\n")
            
            for func in metadata['functions']:
                func_sig = self._format_function_signature(func)
                lines.append(f"### `{func_sig}`\n")
                
                # Docstring
                if func.get('docstring'):
                    lines.append(f"*{func['docstring']}*\n")
                
                # Decorators
                if func.get('decorators'):
                    lines.append("**Decorators:**")
                    for dec in func['decorators']:
                        lines.append(f"- `{dec}`")
                    lines.append("")
                
                # Calls
                if func.get('calls'):
                    lines.append("**Calls:**")
                    for call in func['calls']:
                        call_type = call.get('type', 'unknown')
                        if call.get('module'):
                            lines.append(f"- `{call['name']}` ({call_type}, module: {call['module']})")
                        else:
                            lines.append(f"- `{call['name']}` ({call_type})")
                    lines.append("")
                
                # Returns
                if func.get('returns'):
                    returns_values = [r.get('value', '') for r in func['returns'] if r.get('value')]
                    if returns_values:
                        lines.append("**Returns:**")
                        for ret_val in returns_values:
                            lines.append(f"- `{ret_val}`")
                        lines.append("")
        
        # Comments section (only for level 0)
        if metadata.get('comments'):
            lines.append("## Comments\n")
            for comment in metadata['comments']:
                lines.append(f"- {comment['text']}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_function_signature(self, func: Dict) -> str:
        """Format function signature for display"""
        name = func.get('name', 'unknown')
        params = func.get('parameters', [])
        return_type = func.get('return_type', '')
        
        params_str = ", ".join(params) if params else ""
        
        if return_type:
            return f"{name}({params_str}) -> {return_type}"
        else:
            return f"{name}({params_str})"