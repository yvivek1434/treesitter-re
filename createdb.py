import sqlite3

DB_PATH="codebaseschema.db"

def setUpDataBase(dbpath):
    conn=sqlite3.connect(dbpath)
    cursor=conn.cursor()
    fileQuery="""
                create table if not exists files(
                id integer primary key autoincrement,
                filename text,
                filepath text,
                filetype text
                )        
"""

    metadataQuery="""
        create table if not exists metadata(
        id integer primary key autoincrement,
        fileId integer,
        name text,
        type text,
        codecontent text,
        docstatus integer,
        docContent text,
        foreign key (fileId) references files(id)
        )        
"""

    referencesQuery="""
            create table if not exists referencesTable(
            id1 integer,
            id2 integer,
            primary key (id1,id2),
            foreign key (id1) references metadata(id),
            foreign key (id2) references metadata(id)
            )        
"""
    cursor.execute(fileQuery)
    cursor.execute(metadataQuery)
    cursor.execute(referencesQuery)
    conn.commit()
    conn.close()

def connect_db(db_name='codebaseschema.db'):
    return sqlite3.connect(db_name)

def insert_file(conn, filename, filepath, filetype):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO files (filename, filepath, filetype)
        VALUES (?, ?, ?)
    ''', (filename, filepath, filetype))
    conn.commit()
    return cursor.lastrowid  # Return the ID of the newly inserted file

def insert_metadata(conn, fileId, name, type, codecontent, docstatus, docContent):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO metadata (fileId, name, type, codecontent, docstatus, docContent)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (fileId, name, type, codecontent, docstatus, docContent))
    conn.commit()
    return cursor.lastrowid  # Return the ID of the newly inserted metadata

def insert_reference(conn, id1, id2):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO referencesTable (id1, id2)
        VALUES (?, ?)
    ''', (id1, id2))
    conn.commit()

def get_file_id(conn, filepath):
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM files WHERE filepath = ?', (filepath,))
    result = cursor.fetchone()
    return result[0] if result else None


---------------------------------------------------------------------------------------------------

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
            "code_content": "renderApp() { this.header.renderPageLoadHeader(\"#app\'); this.renderMain('#app'); t",
            "description": "The 'renderApp' method is responsible for rendering the initial structure of the ap",
            "vulnerability": "No direct vulnerabilities identified in the renderApp method."
        }
    ]
}

# Step 1: Build a mapping of file dependencies and functions
dependency_map = defaultdict(list)
for file, entries in input_json.items():
    for entry in entries:
        dependency_map[file].append({
            "dependency_file": entry["code_file"],
            "function_name": entry["name"]
        })

# Step 2: Function to build the hierarchical JSON data
def build_tree(file, visited):
    if file in visited:
        return {"dependencies": {}, "used_functions": {}}  # Prevent circular references

    visited.add(file)
    children = {}
    used_functions = defaultdict(list)

    for dep in dependency_map.get(file, []):
        child_tree = build_tree(dep["dependency_file"], visited)

        if dep["dependency_file"] not in used_functions:
            used_functions[dep["dependency_file"]].append(dep["function_name"])

        for child_dep, funcs in child_tree.get("used_functions", {}).items():
            used_functions[child_dep].extend(funcs)

        children[dep["dependency_file"]] = child_tree

    visited.remove(file)

    return {
        "dependencies": children,
        "used_functions": {dep: list(set(funcs)) for dep, funcs in used_functions.items()}
    }

# Step 3: Create the hierarchical JSON for all root files
visited = set()
tree = {file: build_tree(file, visited) for file in input_json.keys()}

# Step 4: Print the hierarchical JSON
print(json.dumps(tree, indent=4))
