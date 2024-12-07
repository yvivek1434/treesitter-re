from tree_sitter import Language, Parser
import tree_sitter_javascript as tsj
import tree_sitter_typescript as tts 
import os
import json


JAVASCRIPT_LANGUAGE = Language(tsj.language())
TYPESCRIPT_LANGUAGE = Language(tts.language_typescript())

# Initialize parser
parser = Parser(JAVASCRIPT_LANGUAGE)

def parse_file(filepath):
    """Parse a JavaScript/TypeScript file and extract metadata with more comprehensive details."""
    with open(filepath, 'r') as f:
        code = f.read()

    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node

    # Lists to hold the individual items with their content
    imports = []
    exports = []
    functions = []
    function_calls = []
    arrow_functions = []
    jsx_elements = []

    # Separate lists to hold the code content
    imports_content = []
    exports_content = []
    functions_content = []
    function_calls_content = []
    arrow_functions_content = []
    jsx_content = []

    def traverse(node):
        """Recursive function to traverse the AST and extract details."""
        if node.type == 'import_statement':
            import_path = node.child_by_field_name('source').text.decode('utf-8')
            imports.append({"module": import_path, "content": code[node.start_byte:node.end_byte]})
        
        if node.type == 'export_statement':
            export_content = code[node.start_byte:node.end_byte]
            exports_content.append(export_content)

            # Identify exported names
            declaration = node.child_by_field_name('declaration')
            if declaration:
                # Named export or default export
                export_name = declaration.text.decode('utf-8')
                exports.append({"export": export_name, "content": export_content})
            else:
                # Handle cases like "export { foo, bar };"
                named_exports = [
                    child.text.decode('utf-8')
                    for child in node.children
                    if child.type == 'identifier'
                ]
                for named_export in named_exports:
                    exports.append({"export": named_export, "content": export_content})

        if node.type == 'function_declaration':
            function_name = node.child_by_field_name('name').text.decode('utf-8')
            functions.append({"function": function_name, "content": code[node.start_byte:node.end_byte]})
        
        if node.type == 'call_expression':
            function_call = node.child_by_field_name('function')
            if function_call:
                function_name = function_call.text.decode('utf-8')
                function_calls.append({"function": function_name, "content": code[node.start_byte:node.end_byte]})

        if node.type == 'arrow_function':
            arrow_function_content = code[node.start_byte:node.end_byte]
            arrow_functions.append({"function": "arrow_function", "content": arrow_function_content})
        
        if node.type == 'jsx_element':
            jsx_element_content = code[node.start_byte:node.end_byte]
            jsx_elements.append({"element": "jsx_element", "content": jsx_element_content})

        for child in node.children:
            traverse(child)

    traverse(root_node)

    # Return metadata with separated content for each item
    return {
        "file": filepath,
        "imports": imports,
        "exports": exports,
        "functions": functions,
        "function_calls": function_calls,
        "arrow_functions": arrow_functions,
        "jsx_elements": jsx_elements,
        "imports_content": [entry['content'] for entry in imports],
        "exports_content": [entry['content'] for entry in exports],
        "functions_content": [entry['content'] for entry in functions],
        "function_calls_content": [entry['content'] for entry in function_calls],
        "arrow_functions_content": [entry['content'] for entry in arrow_functions],
        "jsx_content": [entry['content'] for entry in jsx_elements],
        "code_content": code
    }


def process_codebase(root_dir):
    """Process all JavaScript/TypeScript files in the codebase and save project structure."""
    metadata = []
    project_structure = {}
    a = 0

    for subdir, _, files in os.walk(root_dir):
        # Get relative directory path from root
        relative_dir = os.path.relpath(subdir, root_dir)
        if relative_dir == ".":
            relative_dir = "/"

        # Initialize the directory in the project structure
        if relative_dir not in project_structure:
            project_structure[relative_dir] = []

        for file in files:
            if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                filepath = os.path.join(subdir, file)
                file_metadata = parse_file(filepath)
                metadata.append(file_metadata)

                # Add file to the project structure
                project_structure[relative_dir].append({
                    "file_name": file,
                    "file_path": filepath
                })

                # Save individual file metadata
                a += 1
                output_path = os.path.join('metadata', f"{file}{a}.json")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(file_metadata, f, indent=4)

    # Save combined metadata
    combined_metadata_path = os.path.join('metadata', 'combined_metadata.json')
    with open(combined_metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

    # Save project structure
    project_structure_path = os.path.join('metadata', 'project_structure.json')
    with open(project_structure_path, 'w') as f:
        json.dump(project_structure, f, indent=4)

    return metadata


import os



import networkx as nx
import matplotlib.pyplot as plt
def get_file_for_function(function_name):
        # Search through metadata to find the file containing the function
        for file in metadata:
            for func in file["function_calls"]:
                if func["function"] == function_name:
                    return file["file"]
        return None

# Normalize file paths for accurate resolution
# Helper function to normalize paths
# Normalize import paths to absolute file paths
# Normalize import paths to absolute file paths
def normalize_path(base_path, import_path):
    import_path = import_path.strip("'\"")
    
    # Exclude non-relative imports (i.e., libraries or node modules)
    if not import_path.startswith("."):
        return None  
    
    # If the import is a relative path (starts with .), join it with the base path
    return os.path.normpath(os.path.join(base_path, import_path))

# Function to find all dependencies of a file recursively
def find_dependencies(file_path, file_mapping, visited_files):
    if file_path in visited_files:
        return []  # Avoid circular dependencies or reprocessing the same file

    visited_files.add(file_path)  # Mark this file as visited
    dependencies = []

    # Get the file's metadata
    file_data = file_mapping.get(file_path)
    if not file_data:
        return dependencies  # If file data isn't found, return empty list

    imports = file_data.get("imports", [])
    for imp in imports:
        module_name = imp['module']
        dependent_file = None

        # Normalize the import path
        normalized_path = normalize_path(os.path.dirname(file_path), module_name)
        if normalized_path:
            # Check if the normalized path exists in the file mapping
            for path in file_mapping:
                # Ensure the file path is normalized and matches the import
                if os.path.normpath(path) == normalized_path:
                    dependent_file = path
                    break
        
        if dependent_file:
            # Add the dependent file to the dependencies list
            dependencies.append(dependent_file)
            # Recursively find the dependencies of this dependent file
            dependencies.extend(find_dependencies(dependent_file, file_mapping, visited_files))

    return dependencies

# Generate the hierarchical dependency structure
def generate_dependency_hierarchy(metadata):
    # Create a mapping of file paths to file metadata for easy lookup
    file_mapping = {file_data['file']: file_data for file_data in metadata}
    
    hierarchy = {}

    # Process each file's metadata to find its dependencies
    for file_data in metadata:
        current_file = file_data['file']
        visited_files = set()  # Set to keep track of files we've already processed

        # Find all dependencies recursively
        all_dependencies = find_dependencies(current_file, file_mapping, visited_files)
        
        # For each dependency, find the functions used in that file (if any)
        dependencies_info = []
        for dep_file in all_dependencies:
            functions_used = []
            dep_file_data = file_mapping.get(dep_file)
            if dep_file_data:
                # Look for functions used from this dependency
                for func_call in file_data.get('function_calls', []):
                    if func_call['function'] in [fc['function'] for fc in dep_file_data.get('function_calls', [])]:
                        functions_used.append(func_call['function'])
            
            dependencies_info.append({
                "dependent_file": dep_file,
                "functions_used_from_this_file": functions_used
            })
        
        # Add the dependencies and function calls info to the hierarchy
        hierarchy[current_file] = {
            "imports": [imp['module'] for imp in file_data.get("imports", [])],
            "function_calls": [call['function'] for call in file_data.get("function_calls", [])],
            "dependent_files": dependencies_info
        }

    return hierarchy
if __name__ == "__main__":
    root_dir = "./testcodebases/react-weather-forecast-master"
    metadata = process_codebase(root_dir)
    #dependency_tree = build_dependency_tree(metadata)

    # Save the dependency tree
    # with open('metadata/dependency_tree.json', 'w') as f:
    #     json.dump(dependency_tree, f, indent=4)

    print("Dependency tree saved to metadata/dependency_tree.json")
    ##--dependency_tree_json = generate_dependency_tree_json(metadata)

    # # Step 2: Print or save the JSON to a file
    # json_output = json.dumps(dependency_tree_json, indent=4)
    # print(json_output)
    root_file = "./testcodebases/react-weather-forecast-master\\src\\index.js"
    G = nx.DiGraph()

        # Process each file and extract its dependencies
    for file in metadata:
        file_name = file["file"]
        G.add_node(file_name)  # Add the file as a node

        # Add dependencies based on imports
        for imp in file["imports"]:
            module = imp["module"]
            G.add_edge(file_name, module)  # Add a directed edge from the file to the imported module

        # Add dependencies based on function calls
        for func_call in file["function_calls"]:
            function = func_call["function"]
            called_file = get_file_for_function(function)  # You would need a way to map function calls to files
            if called_file:
                G.add_edge(file_name, called_file)

    # Function to map function names to files (you need to implement this based on your metadata)
    file_dependencies = {}

# Process each file in the metadata
    for file in metadata:
        file_name = file["file"]
        imports = [imp["module"] for imp in file["imports"]]
        function_calls = [func["function"] for func in file["function_calls"]]
        
        # Add the file and its dependencies (imports + function calls) to the dictionary
        file_dependencies[file_name] = {
            "imports": imports,
            "function_calls": function_calls
        }

    # Convert the dependency structure to a JSON string
    dependency_json = json.dumps(file_dependencies, indent=4)
    # Generate hierarchy
    hierarchy = generate_dependency_hierarchy(metadata)

    # Print or save the hierarchy to a JSON file
    output_file = "dependency_hierarchy_tree.json"
    with open(output_file, "w") as f:
        json.dump(hierarchy, f, indent=4)

    # Output the JSON to a file
    with open("file_dependencies.json", "w") as json_file:
        json_file.write(dependency_json)

    # Visualize the dependency graph
    plt.figure(figsize=(12, 12))
    nx.draw(G, with_labels=True, node_size=2000, node_color="skyblue", font_size=10, font_weight="bold")
    plt.title("File Dependency Hierarchy")
    plt.show()

# Step 2: Generate the unified dependency tree
    #combined_dependency_tree = generate_combined_dependency_tree(metadata, root_file)

    # Optionally, save the result to a JSON file
    # with open("hierarchy_dependency_tree.json", "w") as json_file:
    #     json.dump(dependency_tree_json, json_file, indent=4)
    # with open("combined_dependency_tree.json", "w") as json_file:
    #     json.dump(combined_dependency_tree, json_file, indent=4)

---------------------------------------------------------------------------------------------------------
import json
from collections import defaultdict

# Example JSON input
input_json = {
    "src\\modules\\CurrentWeatherDetails.js": [
        {
            "code_file": "src\\utils\\getTempType.js",
            "type": "function",
            "name": "getTempType",
            "code_content": "export default function getTempType(value) {\n if (value) setToLocalStorage('tempTyp",
            "description": "The 'getTempType` function is exported as the default function from the getTempType.j",
            "vulnerability": "The function relies on local storage, which can be manipulated by the client, potent"
        },
        {
            "code_file": "src\\utils\\getTempType.js",
            "type": "function",
            "name": "getLocalStorage",
            "code_content": "import getLocalStorage from './getLocalStorage';",
            "description": "The 'getLocalStorage function is imported from the 'getLocalStorage.js' file. It is u",
            "vulnerability": "The function's implementati"
        }
    ],
    "src\\index.js": [
        {
            "code_file": "src\\App.js",
            "type": "class",
            "name": "App",
            "code_content": "class App { constructor() { this.header = new Header(); this.footer = new Footer();",
            "description": "The `App' class is the main class imported and instantiated in the 'src\\index.js f",
            "vulnerability": "No direct vulnerabilities identified in the App` class instantiation."
        },
        {
            "code_file": "src\\App.js",
            "type": "method",
            "name": "renderApp",
            "code_content": "renderApp() { this.header.renderPageLoadHeader(\"#app\"); this.renderMain('#app'); t",
            "description": "The 'renderApp' method is responsible for rendering the initial structure of the ap",
            "vulnerability": "No direct vulnerabilities identified in the renderApp method."
        }
    ]
}

# Step 1: Build a mapping of file dependencies and functions
dependency_map = defaultdict(list)
file_functions = defaultdict(list)

# Store functions for each file
for file, entries in input_json.items():
    for entry in entries:
        dependency_map[file].append({
            "dependency_file": entry["code_file"],
            "function_name": entry["name"]
        })
        file_functions[file].append(entry["name"])

# Step 2: Function to build the hierarchical JSON data for each file
def build_tree(file, visited):
    if file in visited:
        return {"functions": []}  # Prevent circular references

    visited.add(file)
    children = {}
    used_functions = set(file_functions[file])  # Start with functions from the current file

    for dep in dependency_map.get(file, []):
        child_tree = build_tree(dep["dependency_file"], visited)

        # Ensure the functions from the child file are included in the parent file's function list
        used_functions.update(child_tree.get("functions", []))

        children[dep["dependency_file"]] = child_tree

    visited.remove(file)

    # If there are no children (leaf node), return the list of functions in the current file
    if not children:
        return {
            "functions": list(used_functions)  # All functions from this leaf file
        }

    return {
        "dependencies": children,
        "functions": list(used_functions)  # All functions used in this file, including dependencies
    }

# Step 3: Create separate hierarchical JSON for each file
visited = set()
separate_hierarchies = {}

# Create the hierarchical JSON for each file separately
for file in input_json.keys():
    separate_hierarchies[file] = build_tree(file, visited)

# Step 4: Print the hierarchical JSON for each file
print(json.dumps(separate_hierarchies, indent=4))

