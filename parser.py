#!/usr/bin/python3
import argparse
import os
import re

class Node:
    def __init__(self, ntype, name, origin_directory):
        self.ntype  = ntype
        self.name   = name
        self.origin_directory = origin_directory
    
    def __str__(self):
        return  str(self.__dict__)


class Buffer:
    def __init__(self, node):
        self.name       = node.name
        if "size" in dir(node):
            self.size = int(node.size)
        if "transfer_destination" in dir(node):
            self.usage |= int(node.transfer_destination) # TODO ?
        if "external" in dir(node):
            self.external = bool(node.external)
        if "hostvisible" in dir(node):
            self.hostvisible = bool(node.hostvisible)

class VertexAttribute:
    def __init__(self, node):
        self.name = node.name
        if "format" in dir(node):
            self.format = node.format


def parse_node(module='', graph_data=''):
    used = count_ignorables(graph_data)


def parse_file(graph_path, module_prefix=""):
    nodes = []
    # Open the base file for reading
    with open(graph_path) as graph_file:
        # Join the base file into a single string, stripping ignoreable characters
        full_graph = strip_ignoreables(''.join(graph_file.readlines()))
        # Parse the raw node information from the base file
        raw_nodes = tokenize(full_graph, {}, module_prefix, os.path.dirname(graph_path) + '/')
        
        # While there are unprocessed modules
        while "Module" in raw_nodes.keys():
            # Collect them into a list and erase the entry
            modules = [module for (name, module) in raw_nodes["Module"].items()]
            del raw_nodes["Module"]
            while modules:
                # Pop the first one.
                node = modules[0]
                modules = modules[1:]
                # ... it requires a path
                if not node.path:
                    print("ERROR:\tModule {name} is missing a path.\nFailed to parse.".format(node))
                    return
                # ... we're using said path to build an absolute one.
                module_path = os.path.abspath(node.origin_directory + node.path)
                # ... insert additional raw data at the front of the queue.
                print("Including Module", node.name, "from", module_path, "...")
                with open(module_path) as module_file:
                    # Assemble the module file, stripping ignoreable characters
                    module_graph = strip_ignoreables(''.join(module_file.readlines()))
                    # Parse the raw node information from the module file
                    raw_nodes = tokenize(module_graph, raw_nodes, node.name + '/', os.path.dirname(module_path) + '/')
        
        # Once all Modules are collected, assemble the resulting nodes
        for (ntype, nodes) in raw_nodes.items():
            if ntype == "DescriptorSet":
                for name, node in nodes.items():
                    print("Found DescriptorSet", node.name)
            elif ntype == "Buffer":
                buffers = {}
                for name, node in nodes.items():
                    buffers[name] = Buffer(node)
                    print("Found Buffer", node.name)
                nodes["Buffer"] = buffers
            elif ntype == "VertexAttribute":
                vertex_attributes = {}
                for name, node in nodes.items():
                    print("Found VertexAttribute", node.name)
                    vertex_attributes[name] = VertexAttribute(node)
                nodes["VertexAttribute"] = vertex_attributes
            else:
                print("Didn't recognize node type", ntype)
"""
full_graph is a rg string
nodes is a dictionary {ntype -> { name -> node} }
"""
def tokenize(full_graph, nodes = {}, module_prefix="", origin_directory=""):
    # Kept for debugging purposes - errors based on line number in RG
    d_lines = full_graph.split("\n")
    d_line_no = 0
    d_line_offset = 0

    active_node = None
    # Number of characters consumed by last loop step
    consumed = 0
    # Characters allowed in Node type, name, attribute name, or attribute value
    allowed_set_head = "[^\[\]=;:]"
    allowed_set_attr = "[^\[\]=;]"
    # Regex for "[<type>:<id>]" capture
    head_re = re.compile("\n*\[({allowed}*):({allowed}*)\]\n*".format(allowed=allowed_set_head))
    # Regex for "<key>=<value>;" capture
    attr_re = re.compile("\n*({allowed}*)=({allowed}*);\n*".format(allowed=allowed_set_attr))
    # Regex for "#<comment>" capture
    comm_re = re.compile("\n*#[^\n]*")
    # While there are tokens to be consumed
    while full_graph:
        
        d_lines_consumed = full_graph[:consumed].count("\n")
        d_line_no += d_lines_consumed
        if d_lines_consumed:
            d_line_offset = consumed - full_graph[:consumed].find("\n") - d_lines_consumed
        else:
            d_line_offset += consumed
        # Throw away whatever was consumed during the last step
        full_graph = full_graph[consumed:]
        consumed = 0
        
        # If there's nothing left, break.
        if not full_graph: break
        
        # Attempt to parse a comment
        comment = comm_re.match(full_graph)
        if comment:
            consumed = comment.span()[1]
            continue

        # Attempt to parse a Node head
        node_head = head_re.match(full_graph)
        if node_head:
            # Update number of chars consumed
            consumed = node_head.span()[1]
            # Node Type
            ntype = node_head.group(1)
            # Node Name
            name = node_head.group(2)
            # Key Pair
            active_node = (ntype, module_prefix + name)
            if not ntype in nodes.keys():
                nodes[ntype] = {}
            elif name in nodes[ntype].keys():
                print(
"ERROR:\tInvalid syntax in render graph near line{}:\n\
\t{}\n\
\t{}^\n\
Duplicate definition of {} '{}'.".format(d_line_no + 1, d_lines[d_line_no], ' ' * d_line_offset, ntype, name)
                )
                return
            # Append new Node to list of nodes
            nodes[ntype][module_prefix + name] = Node(
                    ntype=ntype,
                    name=name,
                    origin_directory=origin_directory
                    )
            continue

        # Attempt to parse a Node attribute
        node_attr = attr_re.match(full_graph)
        if node_attr:
            consumed = node_attr.span()[1]
            if not active_node:
                print(
"ERROR:\tInvalid syntax in render graph near line {}:\n\
\t{}\n\
\t{}^\n\
Attribute defined outside of node.\n\
Failed to parse.".format(d_line_no + 1, d_lines[d_line_no], ' ' * d_line_offset))
                return
            # Append attribute to current Node.
            nodes[active_node[0]][active_node[1]].__dict__[node_attr.group(1)] = node_attr.group(2)
            continue
        print(
"ERROR:\tInvalid syntax in render graph near line {}:\n\
\t{}\n\
\t{}^\n\
Failed to parse.".format(d_line_no + 1, d_lines[d_line_no], ' ' * d_line_offset))
        break
    return nodes

def strip_ignoreables(graph_data):
    result = ""
    for c in graph_data:
        if c not in " \r\t":
            result += c
    return result

def parse_graph(path):
    path = os.path.abspath(path)
    pf = parse_file(path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='RenderGraph file path')
    args = parser.parse_args()
    parse_graph(args.path)
