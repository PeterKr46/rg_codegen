#!/usr/bin/python3
import argparse
import os
import re

class Parser:
    def __init__(self):
        self.nodes = []
        self.state = []

class Node:
    def __init__(self, ntype, name, origin_directory):
        self.ntype  = ntype
        self.name   = name
        self.origin_directory = origin_directory
    
    def __str__(self):
        return  str(self.__dict__)

def parse_node(module='', graph_data=''):
    used = count_ignorables(graph_data)


def parse_file(graph_path, module_prefix=""):
    nodes = []
    # Open the base file for reading
    with open(graph_path) as graph_file:
        # Join the base file into a single string, stripping ignoreable characters
        full_graph = strip_ignoreables(''.join(graph_file.readlines()))
        # Parse the raw node information from the base file
        raw_nodes = tokenize(full_graph, module_prefix, os.path.dirname(graph_path) + '/')
        print("Found", len(raw_nodes), "nodes")
        # While there are unprocessed nodes
        while raw_nodes:
            # Pop the first one.
            node = raw_nodes[0]
            raw_nodes = raw_nodes[1:]

            # If it's a module...
            if node.ntype == "Module":
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
                    # Parse the raw node information from the base file
                    module_nodes = tokenize(module_graph, node.name + '/', os.path.dirname(module_path) + '/')
                    print("Found", len(module_nodes), "nodes")
                    # Push new nodes to the front of the work queue.
                    raw_nodes = module_nodes + raw_nodes
            elif node.ntype == "DescriptorSet":
                
            else:
                print("Found Node {name}".format(**node.__dict__))

def tokenize(full_graph, module_prefix="", origin_directory=""):
    # Kept for debugging purposes - errors based on line number in RG
    d_lines = full_graph.split("\n")
    d_line_no = 0
    d_line_offset = 0

    nodes = []
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
            consumed = node_head.span()[1]
            
            # Append new Node to list of nodes
            nodes.append(Node(
                    ntype=node_head.group(1),
                    name=module_prefix + node_head.group(2),
                    origin_directory=origin_directory
                    ))
            continue

        # Attempt to parse a Node attribute
        node_attr = attr_re.match(full_graph)
        if node_attr:
            consumed = node_attr.span()[1]
            if not nodes:
                print(
"ERROR:\tInvalid syntax in render graph near line {}:\n\
\t{}\n\
\t{}^\n\
Attribute defined outside of node.\n\
Failed to parse.".format(d_line_no + 1, d_lines[d_line_no], ' ' * d_line_offset))
                return
            # Append attribute to current Node.
            nodes[-1].__dict__[node_attr.group(1)] = node_attr.group(2)
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
