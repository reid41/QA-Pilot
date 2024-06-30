import json
import os
import subprocess
from typing import Dict, List, Any
import re


def process_nodes(nodes: Dict[str, Any]) -> Dict[str, Any]:
    nodeDataArray = []
    linkDataArray = []
    methods = {}
    types = {}

    for key, node in nodes.items():
        print(f"Processing node: {key} -> {node}")

        if node["Type"] == "import":
            node_data = {
                "key": key,
                "name": node["Name"],
                "class": node["Type"],
                "source": "import " + node["Code"]
            }
            nodeDataArray.append(node_data)
        elif node["Type"] == "type":
            types[key] = node
            node_data = {
                "key": key,
                "name": node["Name"],
                "class": "struct",
                "source": "type " + node["Code"]
            }
            nodeDataArray.append(node_data)
        elif node["Type"] == "method":
            receiver_type = extract_receiver_type(key)
            method_name = extract_method_name(key)
            node_data = {
                "key": f"{receiver_type}.{method_name}",
                "name": method_name,
                "class": node["Type"],
                "source": node["Code"]
            }
            nodeDataArray.append(node_data)

            if receiver_type not in methods:
                methods[receiver_type] = []
            methods[receiver_type].append(node_data)
        elif node["Type"] == "func":
            node_data = {
                "key": key,
                "name": node["Name"],
                "class": "function",
                "source": node["Code"]
            }
            nodeDataArray.append(node_data)
        else:
            node_data = {
                "key": key,
                "name": node["Name"],
                "class": node["Type"],
                "source": node["Code"]
            }
            nodeDataArray.append(node_data)

    for receiver_type, method_list in methods.items():
        if receiver_type in types:
            for method in method_list:
                link = {
                    "from": receiver_type,
                    "to": method["key"],
                    "category": "dashed",
                    "color": "gray"
                }
                linkDataArray.append(link)

    for node_key, node in nodes.items():
        for call in node["Calls"]:
            print(f"Checking call from {node_key} to {call}")
            if call in nodes:
                link = {
                    "from": node_key,
                    "to": call,
                    "category": "dashed",
                    "color": "green"
                }
                linkDataArray.append(link)
                print(f"Link added: {link}")
            else:
                print(f"Call {call} not found in nodes")

    print(f"Final nodeDataArray: {nodeDataArray}")
    print(f"Final linkDataArray: {linkDataArray}")

    return {"nodeDataArray": nodeDataArray, "linkDataArray": linkDataArray}


def extract_receiver_type(key: str) -> str:
    if key.startswith("&"):
        parts = re.split(r'[{}]', key)
        receiver_type = parts[1].strip().split(' ')[-1]
    else:
        receiver_type = key.split(".")[0]

    # Remove generic type parameters if present
    receiver_type = re.sub(r'\[.*?\]', '', receiver_type).strip()
    return receiver_type


def extract_method_name(key: str) -> str:
    return key.split(".")[-1]


def parse_go_code(filepath: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(['./parser', filepath], capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        nodes = json.loads(output)
        return process_nodes(nodes)
    except subprocess.CalledProcessError as e:
        print(f"Error running parser: {e.stderr}")
        return {"nodeDataArray": [], "linkDataArray": []}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return {"nodeDataArray": [], "linkDataArray": []}


def go_build_file_tree(directory: str) -> List[Dict[str, Any]]:
    file_tree = []
    for root, dirs, files in os.walk(directory):
        for d in dirs:
            dir_path = os.path.join(root, d)
            file_tree.append({
                'name': d,
                'path': dir_path,
                'type': 'directory',
                'children': go_build_file_tree(dir_path)
            })
        for f in files:
            if f.endswith('.go'):
                file_path = os.path.join(root, f)
                file_tree.append({
                    'name': f,
                    'path': file_path,
                    'type': 'file'
                })
        break  # Only traverse current directory, not recursively
    return file_tree
