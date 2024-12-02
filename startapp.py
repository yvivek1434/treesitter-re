from tree_sitter import Language, Parser
import tree_sitter_javascript as tsj
import tree_sitter_typescript as tts 
import os
import json
import sqlite3
from db.createdb import connect_db,DB_PATH,insert_file,insert_metadata,insert_reference,setUpDataBase, get_file_id


JAVASCRIPT_LANGUAGE = Language(tsj.language())
TYPESCRIPT_LANGUAGE = Language(tts.language_typescript())

# Initialize parser
parser = Parser(JAVASCRIPT_LANGUAGE)

def parse_file(filepath,conn):
    """Parse a JavaScript/TypeScript file and extract metadata with more comprehensive details."""
    filename = os.path.basename(filepath)
    filetype = os.path.splitext(filepath)[1]
    insert_file(conn, filename, filepath, filetype)
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

    file_id = get_file_id(conn, filepath)

    if not file_id:
        print(f"File path {filepath} not found in files table.")
        fileId=747474
    #print(filepath,"  --  ",fileId)
    # Insert metadata using the helper function
    for entry in imports:
        insert_metadata(conn, file_id, entry['module'], 'import_statement', entry['content'], 0, None)

    for entry in functions:
        insert_metadata(conn, file_id, entry['function'], 'function_declaration', entry['content'], 0, None)

    for entry in function_calls:
        insert_metadata(conn, file_id, entry['function'], 'function_call', entry['content'], 0, None)

    for entry in arrow_functions:
        insert_metadata(conn, file_id, 'lambda', 'arrow_function', entry['content'], 0, None)

    for entry in jsx_elements:
        insert_metadata(conn, file_id, 'jsx', 'jsx_content', entry['content'], 0, None)

    # Insert raw code content
    insert_metadata(conn, file_id, 'jscontent', 'code_content', code, 0, None)


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


def process_codebase(root_dir,conn):
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
            filetype = os.path.splitext(file)[1][1:] 
            if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                filepath = os.path.join(subdir, file)
                file_metadata = parse_file(filepath,conn)
                
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


import subprocess
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel, Field
from tqdm import tqdm
BASE_DIR: Path= Path(__name__).resolve().parent

class Reference(BaseModel):
    type: str = Field(description="Type of Statement")
    name: str = Field(description="name of function")
    code_content: str= Field(description="code content")
    description: str = Field(description="Description of code")

def get_dependency_tree(filepath:str):
    try:
        result=subprocess.run(
            [
                "node",
                f"{BASE_DIR}/node_modules/madge/bin/cli.js",
                "--json",
                filepath,
            ],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        raise e
def readFile(filepath):
    with open(filepath,"r",encoding="latin1") as f:
        content=f.read()
    return content
def create_proj_dep_metadata(reppath:str):
    depTree: Dict= get_dependency_tree(reppath)
    keys:list[str]=sorted(depTree,key=lambda k : len(depTree[k]))
    meta_data:Dict ={}
    for key in tqdm(keys,"Creating dependency"):
        file_path=os.path.join(reppath,key.replace("/","\\"))
        depends_on:list[str] = depTree[key]
        code_content=readFile(file_path)
        data: List[Reference]=[]

        for depend_on in depends_on:
            depend_on_file_path=os.path.join(reppath,depend_on.replace("/","\\"))
            depends_on_content=readFile(depend_on_file_path)
            data.append(
                {
                    "name":depend_on,
                    # "code_content":code_content,
                    # "reference_code":depends_on_content,
                }
            )
        meta_data[key]=data
    print("saving depenedencydata using madge")
    madge_dep_path=os.path.join('metadata',"dependency_metadata_using_madge.json")
    with open(madge_dep_path,'w') as f:
        json.dump(meta_data,f,indent=4)
    print("created madge")
# Read the JSON file
def read_dependency_data(file_path: str) -> Dict[str, List[Dict[str, str]]]:
    """Read the dependency data from a JSON file and return as a dictionary."""
    with open(file_path, 'r') as file:
        return json.load(file)

def build_dependency_tree(metadata: Dict[str, List[Dict[str, str]]], root: str) -> Dict:
    """Recursively build the dependency tree."""
    tree = {root: []}
    for dependency in metadata.get(root, []):
        dep_name = dependency["name"]
        tree[root].append(build_dependency_tree(metadata, dep_name))
    return tree

def find_root_files(metadata: Dict[str, List[Dict[str, str]]]) -> List[str]:
    """Find files that are not dependencies of any other file."""
    all_files = set(metadata.keys())
    dependent_files = {dep["name"] for deps in metadata.values() for dep in deps}
    root_files = list(all_files - dependent_files)
    return root_files

def build_hierarchical_dependency_tree(metadata: Dict[str, List[Dict[str, str]]]) -> Dict:
    """Build a full hierarchical dependency tree for all root files."""
    root_files = find_root_files(metadata)
    tree = {}
    for root in root_files:
        tree.update(build_dependency_tree(metadata, root))
    return tree


if __name__ == "__main__":
    root_dir = "./testcodebases/react-weather-forecast-master"
    setUpDataBase(DB_PATH)
    conn = connect_db()
    metadata = process_codebase(root_dir,conn)
    # json_file = './metadata/combined_metadata.json'  # Path to your JSON file

    # populate_metadata_table(json_file, conn)
    conn.close()
    create_proj_dep_metadata(root_dir)
    dependency_data=readFile("./metadata/dependency_metadata_using_madge.json")
    if isinstance(dependency_data, str):
        dependency_data = json.loads(dependency_data)
    dependency_tree = build_hierarchical_dependency_tree(dependency_data)

    madge_dep_hieracht_tree_path=os.path.join('metadata',"dependency_metadata_hieracht_tree_using_madge.json")
    with open(madge_dep_hieracht_tree_path,'w') as f:
        json.dump(dependency_tree,f,indent=4)

    print("created madge hierarchy")
    #dependency_tree = build_dependency_tree(metadata)

    # Save the dependency tree
    # with open('metadata/dependency_tree.json', 'w') as f:
    #     json.dump(dependency_tree, f, indent=4)
   
    print("Dependency tree saved to metadata/dependency_tree.json")
    ##--dependency_tree_json = generate_dependency_tree_json(metadata)

    # # Step 2: Print or save the JSON to a file
    # json_output = json.dumps(dependency_tree_json, indent=4)
    # print(json_output)
   