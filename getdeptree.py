import subprocess
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel, Field
from tqdm import tqdm
import json
import os
def readFile(filepath):
    with open(filepath,"r",encoding="utf8") as f:
        content=f.read()
    return content

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

dependency_data=readFile("./metadata/dependency_metadata_using_madge.json")
if isinstance(dependency_data, str):
    dependency_data = json.loads(dependency_data)
dependency_tree = build_hierarchical_dependency_tree(dependency_data)
madge_dep_hieracht_tree_path=os.path.join('metadata',"dependency_metadata_hieracht_tree_using_madge.json")
with open(madge_dep_hieracht_tree_path,'w') as f:
    json.dump(dependency_tree,f,indent=4)
print("created madge hierarchy")