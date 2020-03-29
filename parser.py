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

class Image:
    def __init__(self, node):
        print("Created",str(type(self)), node.name)


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

class Shader:
    def __init__(self, node):
        print("Created",str(type(self)), node.name)

class Asset:
    def __init__(self, node):
        print("Created",str(type(self)), node.name)

class AccelerationStructure:
    def __init__(self, node):
        print("Created",str(type(self)), node.name)

class Pipeline:
    def __init__(self, node):
        print("Created",str(type(self)), node.name)

class DescriptorSet:
    def __init__(self, node):
        print("Created",str(type(self)), node.name)

class RenderPass:
    def __init__(self, node):
        print("Created",str(type(self)), node.name)



class Graph:
    def __init__(self):
        self.v = "0.01"


class Parser:
    def __init__(self, rg_path, module_prefix = ""):
        # .rg path
        self.rg_path = rg_path
        # vector of raw node data
        self.rg_nodes = []
        # map from node name to node data index
        self.rg_map = {}
        # a prefix to add in front of all resulting nodes
        self.module_prefix = module_prefix
        # Graph could be Assembled here.
        self.graph = None

    def maybe_create_node(self, node):
        if self.graph:
            if not "nodes_" + node.ntype in self.graph.__dict__.keys():
                self.graph.__dict__["nodes_" + node.ntype] = []
                self.graph.__dict__["map_" + node.ntype] = {}
            self.graph.__dict__["map_" + node.ntype][node.name] = len(self.graph.__dict__["nodes_" + node.ntype])
            # TODO might be dangerous.
            self.graph.__dict__["nodes_" + node.ntype].append(None) 
        self.rg_nodes.append(node)


    def parse(self, assemble = True):
        # Initialize empty graph if necessary.
        self.graph = None if not assemble else Graph()

        print("Parsing", self.rg_path)
        # transform the file into a set of untyped Nodes
        raw_nodes = tokenize_file(self.rg_path, self.module_prefix)
        if not raw_nodes:
            return
        # iterate the Nodes
        for (_, node) in raw_nodes.items():
            # If the Node is a Module, it gets special handling.
            if node.ntype == "Module":
                if not "path" in dir(node):
                    print("ERROR:\tModule {} is missing a path.\nFailed to parse.".format(node))
                # Create a new Parser
                module_parser = Parser(os.path.abspath(node.origin_directory + node.path), node.name + '/')
                # Parse only the raw data from this one.
                if not module_parser.parse(False):
                    print("ERROR:\tModule {} could not be parsed properly.".format(node.path))
                    return
                # Iterate the nodes defined in this module
                for module_node in module_parser.rg_nodes:
                    # Duplicates are handled as errors
                    if module_node.name in self.rg_map.keys():
                        print("ERROR:\tDuplicate definition of {} {} in {}".format(module_parser.rg_nodes[node_idx].ntype, name, node.name))
                        return
                    else:
                        # Insert newly typed node into own set.
                        self.maybe_create_node(module_node)
            else:
                self.maybe_create_node(node)
        # After we've successfully parsed all raw data, assemble if told to.
        if assemble:
            self.parse_nodes(Image)
            self.parse_nodes(Buffer)
            
            self.parse_nodes(VertexAttribute)
            self.parse_nodes(Shader)
            
            self.parse_nodes(Asset)
            self.parse_nodes(AccelerationStructure)
            self.parse_nodes(Pipeline)
            self.parse_nodes(DescriptorSet)

            self.parse_nodes(RenderPass)
        return True
               

    def parse_nodes(self, ntype_t):
        print("Building",ntype_t.__name__,"nodes...")
        for node in self.rg_nodes:
            if node.ntype == ntype_t.__name__:
                img_idx = self.graph.__dict__["map_" + ntype_t.__name__][node.name]
                self.graph.__dict__["nodes_" + ntype_t.__name__][img_idx] = ntype_t(node)

def tokenize_file(graph_path, module_prefix=""):
    nodes = []
    # Open the base file for reading
    with open(graph_path) as graph_file:
        # Join the base file into a single string, stripping ignoreable characters
        full_graph = strip_ignoreables(''.join(graph_file.readlines()))
        # Parse the raw node information from the base file
        return tokenize(full_graph, module_prefix, os.path.dirname(graph_path) + '/')

"""
full_graph is a rg string
nodes is a dictionary {ntype -> { name -> node} }
"""
def tokenize(full_graph, module_prefix="", origin_directory=""):
    # Kept for debugging purposes - errors based on line number in RG
    d_lines = full_graph.split("\n")
    d_line_no = 0
    d_line_offset = 0

    nodes = {}
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
            name = module_prefix + node_head.group(2)
            # Key Pair
            active_node = ntype + ":" + name
            if name in nodes.keys():
                print(
"ERROR:\tInvalid syntax in render graph near line{}:\n\
\t{}\n\
\t{}^\n\
Duplicate definition of {} '{}'.".format(d_line_no + 1, d_lines[d_line_no], ' ' * d_line_offset, ntype, name)
                )
                return
            # Append new Node to list of nodes
            nodes[active_node] = Node(
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
            nodes[active_node].__dict__[node_attr.group(1)] = node_attr.group(2)
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='RenderGraph file path')
    args = parser.parse_args()
    rg_parser = Parser(args.path)
    if rg_parser.parse():
        for node in rg_parser.rg_nodes:
            print(str(node))
