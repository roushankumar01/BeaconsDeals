import argparse
import ast
import json
import os
import networkx as nx

class CodeVisitor(ast.NodeVisitor):
    def __init__(self, filepath, module_name):
        self.filepath = filepath
        self.module_name = module_name
        self.classes = []
        self.methods = []
        self.functions = []
        self.imports = []
        self.calls = []

        self.current_class = None
        self.current_function = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({"module": alias.name, "name": alias.name})
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module if node.module else ""
        for alias in node.names:
            self.imports.append({"module": module, "name": alias.name})
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_info = {
            "name": node.name,
            "id": f"{self.module_name}.{node.name}",
            "bases": [b.id for b in node.bases if isinstance(b, ast.Name)]
        }
        self.classes.append(class_info)

        prev_class = self.current_class
        self.current_class = class_info["id"]
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        func_info = {
            "name": node.name,
            "id": f"{self.current_class}.{node.name}" if self.current_class else f"{self.module_name}.{node.name}",
            "is_method": self.current_class is not None,
            "parent_class": self.current_class
        }
        if func_info["is_method"]:
            self.methods.append(func_info)
        else:
            self.functions.append(func_info)

        prev_function = self.current_function
        self.current_function = func_info["id"]
        self.generic_visit(node)
        self.current_function = prev_function

    def visit_Call(self, node):
        if self.current_function:
            callee_name = None
            if isinstance(node.func, ast.Name):
                callee_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee_name = node.func.attr

            if callee_name:
                self.calls.append({
                    "caller": self.current_function,
                    "callee": callee_name # Note: Resolving exact callee ID across files requires a multi-pass approach or type inference, keeping it simple as callee name here.
                })
        self.generic_visit(node)

def index_project(project_path, project_name, language, registry_path):
    graph = nx.DiGraph()

    # 1. Parse all files
    parsed_modules = {}
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, project_path)
                module_name = rel_path.replace(os.sep, '.')[:-3]

                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read(), filename=filepath)
                        visitor = CodeVisitor(filepath, module_name)
                        visitor.visit(tree)
                        parsed_modules[module_name] = {
                            "filepath": rel_path,
                            "visitor": visitor
                        }
                    except SyntaxError as e:
                        print(f"Syntax error in {filepath}: {e}")

    # 2. Build Graph Nodes
    for module_name, data in parsed_modules.items():
        rel_path = data["filepath"]
        visitor = data["visitor"]

        # Add file node
        graph.add_node(module_name, type="file", label=rel_path)

        # Add class nodes
        for cls in visitor.classes:
            graph.add_node(cls["id"], type="class", label=cls["name"])
            graph.add_edge(module_name, cls["id"], type="contains")

        # Add method nodes
        for method in visitor.methods:
            graph.add_node(method["id"], type="method", label=method["name"])
            graph.add_edge(method["parent_class"], method["id"], type="contains")

        # Add function nodes
        for func in visitor.functions:
            graph.add_node(func["id"], type="function", label=func["name"])
            graph.add_edge(module_name, func["id"], type="contains")

    # 3. Build Graph Edges (Relationships)
    for module_name, data in parsed_modules.items():
        visitor = data["visitor"]

        # Imports
        for imp in visitor.imports:
            # Simplistic import resolution (module level)
            if imp["module"] in parsed_modules:
                graph.add_edge(module_name, imp["module"], type="imports")
            elif imp["name"] in parsed_modules:
                graph.add_edge(module_name, imp["name"], type="imports")

        # Inheritance
        for cls in visitor.classes:
            for base in cls["bases"]:
                # Try to find base class in the same module
                base_id = f"{module_name}.{base}"
                if base_id in graph.nodes:
                    graph.add_edge(cls["id"], base_id, type="inherits")
                else:
                    # Very naive cross-module inheritance resolution
                    for other_mod, other_data in parsed_modules.items():
                        potential_base_id = f"{other_mod}.{base}"
                        if potential_base_id in graph.nodes:
                            graph.add_edge(cls["id"], potential_base_id, type="inherits")
                            break

        # Calls (Naive)
        for call in visitor.calls:
            caller = call["caller"]
            callee_name = call["callee"]

            # Find potential callees by name
            for node_id, node_data in graph.nodes(data=True):
                if node_data.get("label") == callee_name and node_data.get("type") in ["method", "function", "class"]:
                    graph.add_edge(caller, node_id, type="calls")

    # 4. Export Graph
    # NetworkX defaults to 'links', but our frontend expects 'edges'
    graph_data = nx.node_link_data(graph, edges="edges")
    graph_out_path = os.path.join(project_path, 'graph.json')
    with open(graph_out_path, 'w') as f:
        json.dump(graph_data, f, indent=2)
    print(f"Generated graph at {graph_out_path}")

    # 5. Update Registry
    registry = []
    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            try:
                registry = json.load(f)
            except json.JSONDecodeError:
                pass

    # Update or add
    project_entry = {
        "name": project_name,
        "language": language,
        "path": project_path,
        "graph_file": "graph.json"
    }

    found = False
    for i, entry in enumerate(registry):
        if entry["name"] == project_name:
            registry[i] = project_entry
            found = True
            break

    if not found:
        registry.append(project_entry)

    os.makedirs(os.path.dirname(os.path.abspath(registry_path)), exist_ok=True)
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    print(f"Updated registry at {registry_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python Code Indexer")
    parser.add_argument("--path", required=True, help="Path to project to index")
    parser.add_argument("--name", required=True, help="Project name")
    parser.add_argument("--language", default="python", help="Programming language")
    parser.add_argument("--registry", required=True, help="Path to registry.json")

    args = parser.parse_args()

    index_project(args.path, args.name, args.language, args.registry)
