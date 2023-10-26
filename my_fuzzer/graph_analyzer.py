class GraphNode:
    def __init__(self, name):
        self.name = name
        self.neighbors = dict()  # node_name -> a list of rule index

    def add_neighbor(self, neighbor_name, rule_id):
        if neighbor_name in self.neighbors:
            self.neighbors[neighbor_name].append(rule_id)
        else:
            self.neighbors[neighbor_name] = [rule_id]


class DirectedGraphNode:
    def __init__(self, name):
        self.name = name
        self.children = dict()
        self.parents = dict()

    def add_child(self, child_name, rule_id):
        if child_name in self.children:
            self.children[child_name].append(rule_id)
        else:
            self.children[child_name] = [rule_id]

    def add_parent(self, parent_name, rule_id):
        if parent_name in self.parents:
            self.parents[parent_name].append(rule_id)
        else:
            self.parents[parent_name] = [rule_id]


class Graph:
    def __init__(self):
        self.nodes = dict()  # node_name -> Node
        self.rules = []
        self.interface_list = []
        self.blacklist = {'double', 'int', 'float', 'import', "DOMString", "short", "unsigned long",
                          "long long", "unsigned", "unsigned long long", "long", "boolean",
                          "fuzzint", "EventHandler", "EventTarget", "DOMException", "DOMStringList"}

    def is_interesting_interface(self, name) -> bool:
        # if name not in self.interface_list:
        #     return False
        if name in self.blacklist:
            return False
        return True

    def add_node(self, name) -> bool:
        if not self.is_interesting_interface(name):
            return False
        if name not in self.nodes:
            self.nodes[name] = GraphNode(name)
            return True
        else:
            return False

    def add_rule(self, rule) -> int:
        self.rules.append(rule)
        return len(self.rules) - 1

    def add_edge(self, node_name_1, node_name_2, rule_id) -> bool:
        if not self.is_interesting_interface(node_name_1):
            return False
        if not self.is_interesting_interface(node_name_2):
            return False
        if (node_name_1 not in self.nodes) or (node_name_2 not in self.nodes):
            return False
        node_1 = self.nodes[node_name_1]
        node_2 = self.nodes[node_name_2]
        node_1.add_neighbor(node_name_2, rule_id)
        node_2.add_neighbor(node_name_1, rule_id)
        # node_1.add_child(node_name_2, rule_id)
        # node_2.add_parent(node_name_1, rule_id)
        return True


def dfs(node_name, graph, visited):
    if node_name in visited:
        return []
    visited.add(node_name)
    res = [node_name]
    for child_name in graph.nodes[node_name].neighbors.keys():
        res += dfs(child_name, graph, visited)
    return res


def divide_into_groups(graph: Graph):
    visited = set()
    groups = []
    for node_name in sorted(list(graph.nodes.keys())):
        if node_name not in visited:
            groups.append(dfs(node_name, graph, visited))
    # print(groups[1])
    for group in groups:
        print(group)
