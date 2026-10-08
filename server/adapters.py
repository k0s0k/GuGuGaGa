"""Generate readable, standalone stdin/stdout programs from LeetCode methods."""
import ast
import copy
import io
import json
import re
import shlex
import textwrap
import tokenize

PY_IMPORTS = '''from typing import *
from collections import deque, defaultdict, Counter, OrderedDict
import heapq
import bisect
import math
import json
import shlex
import sys
sys.setrecursionlimit(100000)
'''
PY_NODES = '''
class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right

class Node:
    def __init__(self, x=0, next=None, random=None):
        self.val, self.next, self.random = x, next, random
'''
PY_HELPERS = '''
def make_list(values):
    dummy = tail = ListNode()
    for value in values:
        tail.next = ListNode(value)
        tail = tail.next
    return dummy.next

def list_nodes(head):
    nodes, visited = [], set()
    while head:
        if id(head) in visited:
            raise ValueError('输出链表的 next 中出现了意外的环')
        visited.add(id(head))
        nodes.append(head)
        head = head.next
    return nodes

def make_tree(values):
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue = deque([root])
    index = 1
    while queue and index < len(values):
        node = queue.popleft()
        for side in ('left', 'right'):
            if index < len(values) and values[index] is not None:
                child = TreeNode(values[index])
                setattr(node, side, child)
                queue.append(child)
            index += 1
    return root

def find_node(root, value):
    if root is None or root.val == value:
        return root
    return find_node(root.left, value) or find_node(root.right, value)

def to_value(value):
    if isinstance(value, TreeNode):
        queue, result = deque([value]), []
        while queue:
            node = queue.popleft()
            result.append(node.val if node else None)
            if node:
                queue.extend([node.left, node.right])
        while result and result[-1] is None:
            result.pop()
        return result
    if isinstance(value, ListNode):
        return [node.val for node in list_nodes(value)]
    if isinstance(value, Node):
        nodes = list_nodes(value)
        indices = {id(node): i for i, node in enumerate(nodes)}
        return [[node.val, indices.get(id(node.random))] for node in nodes]
    return value

def read_argument(kind):
    if kind in ('int', 'double'):
        return (int if kind == 'int' else float)(input())
    if kind == 'string':
        return json.loads(input())
    if kind in ('ListNode', 'TreeNode'):
        count = int(input())
        values = [None if x == 'null' else int(x) for x in input().split()]
        if len(values) != count:
            raise ValueError('节点数量与输入不一致')
        return make_list(values) if kind == 'ListNode' else make_tree(values)
    if kind == 'ListNode[]':
        return [read_argument('ListNode') for _ in range(int(input()))]
    if kind == 'Node':
        count = int(input())
        pairs = [list(map(int, input().split())) for _ in range(count)]
        nodes = [Node(pair[0]) for pair in pairs]
        for i, (_, random_index) in enumerate(pairs):
            nodes[i].next = nodes[i + 1] if i + 1 < count else None
            nodes[i].random = nodes[random_index] if random_index >= 0 else None
        return nodes[0] if nodes else None
    if kind in ('int[]', 'string[]'):
        count = int(input())
        values = list(map(int, input().split())) if kind == 'int[]' else shlex.split(input())
        if len(values) != count:
            raise ValueError('数组长度与输入不一致')
        return values
    if kind in ('int[][]', 'char[][]'):
        rows, columns = map(int, input().split())
        matrix = []
        for _ in range(rows):
            row = list(map(int, input().split())) if kind == 'int[][]' else shlex.split(input())
            if len(row) != columns:
                raise ValueError('矩阵列数与输入不一致')
            matrix.append(row)
        return matrix
    raise ValueError('未知参数类型: ' + kind)
'''

CPP_IMPORTS = '''#include <algorithm>
#include <array>
#include <bitset>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <functional>
#include <iomanip>
#include <iostream>
#include <list>
#include <map>
#include <numeric>
#include <queue>
#include <random>
#include <set>
#include <sstream>
#include <stack>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
using namespace std;
'''
CPP_NODES = '''
struct ListNode {
    int val; ListNode* next;
    ListNode(int x = 0, ListNode* n = nullptr) : val(x), next(n) {}
};
struct TreeNode {
    int val; TreeNode *left, *right;
    TreeNode(int x = 0, TreeNode* l = nullptr, TreeNode* r = nullptr) : val(x), left(l), right(r) {}
};
class Node {
public:
    int val; Node *next, *random;
    Node(int x = 0) : val(x), next(nullptr), random(nullptr) {}
};
'''
CPP_HELPERS = r'''
template<class T> void readValue(T& value) { cin >> value; }
void readValue(string& value) {
    cin >> ws;
    char c;
    if (!cin.get(c) || c != '"') throw invalid_argument("Expected a JSON string");
    value.clear();
    auto hex4 = [&]() {
        unsigned result = 0;
        for (int i = 0; i < 4; ++i) {
            if (!cin.get(c)) throw invalid_argument("Incomplete Unicode escape");
            int digit = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
            if (digit < 0) throw invalid_argument("Invalid Unicode escape");
            result = result * 16 + digit;
        }
        return result;
    };
    while (cin.get(c)) {
        if (c == '"') return;
        if (c != '\\') {
            if ((unsigned char)c < 32) throw invalid_argument("Unescaped control character");
            value += c;
            continue;
        }
        if (!cin.get(c)) break;
        switch (c) {
            case '"': case '\\': case '/': value += c; break;
            case 'b': value += '\b'; break;
            case 'f': value += '\f'; break;
            case 'n': value += '\n'; break;
            case 'r': value += '\r'; break;
            case 't': value += '\t'; break;
            case 'u': {
                unsigned point = hex4();
                if (point >= 0xD800 && point <= 0xDBFF) {
                    if (!cin.get(c) || c != '\\' || !cin.get(c) || c != 'u') throw invalid_argument("Missing low surrogate");
                    unsigned low = hex4();
                    if (low < 0xDC00 || low > 0xDFFF) throw invalid_argument("Invalid low surrogate");
                    point = 0x10000 + ((point - 0xD800) << 10) + low - 0xDC00;
                } else if (point >= 0xDC00 && point <= 0xDFFF) throw invalid_argument("Unexpected low surrogate");
                if (point < 0x80) value += (char)point;
                else {
                    if (point >= 0x10000) value += (char)(0xF0 | (point >> 18));
                    if (point >= 0x800) value += (char)((point < 0x10000 ? 0xE0 : 0x80) | ((point >> 12) & 0x3F));
                    value += (char)((point < 0x800 ? 0xC0 : 0x80) | ((point >> 6) & 0x3F));
                    value += (char)(0x80 | (point & 0x3F));
                }
                break;
            }
            default: throw invalid_argument("Invalid JSON escape");
        }
    }
    throw invalid_argument("Unterminated JSON string");
}
template<class T> void readValue(vector<T>& values) {
    int count; cin >> count; values.resize(count);
    for (auto& value : values) readValue(value);
}
template<class T> void readMatrix(vector<vector<T>>& matrix) {
    int rows, cols; cin >> rows >> cols;
    matrix.assign(rows, vector<T>(cols));
    for (auto& row : matrix) for (auto& value : row) readValue(value);
}
void readValue(ListNode*& head) {
    int count; cin >> count; ListNode dummy; auto tail = &dummy;
    for (int i = 0, x; i < count; ++i) {
        cin >> x; tail->next = new ListNode(x); tail = tail->next;
    }
    head = dummy.next;
}
void readValue(TreeNode*& root) {
    int count; cin >> count; vector<string> values(count);
    for (auto& value : values) cin >> value;
    root = nullptr;
    if (count == 0 || values[0] == "null") return;
    root = new TreeNode(stoi(values[0])); queue<TreeNode*> pending; pending.push(root);
    int index = 1;
    while (!pending.empty() && index < count) {
        auto node = pending.front(); pending.pop();
        if (values[index] != "null") { node->left = new TreeNode(stoi(values[index])); pending.push(node->left); }
        ++index;
        if (index < count && values[index] != "null") { node->right = new TreeNode(stoi(values[index])); pending.push(node->right); }
        ++index;
    }
}
void readValue(vector<ListNode*>& values) {
    int count; cin >> count; values.resize(count);
    for (auto& value : values) readValue(value);
}
void readValue(Node*& head) {
    int count; cin >> count; vector<Node*> nodes(count); vector<int> randoms(count);
    for (int i = 0, x; i < count; ++i) { cin >> x >> randoms[i]; nodes[i] = new Node(x); }
    for (int i = 0; i < count; ++i) {
        nodes[i]->next = i + 1 < count ? nodes[i + 1] : nullptr;
        nodes[i]->random = randoms[i] < 0 ? nullptr : nodes[randoms[i]];
    }
    head = count ? nodes[0] : nullptr;
}
TreeNode* findNode(TreeNode* root, int value) {
    if (!root || root->val == value) return root;
    auto left = findNode(root->left, value);
    return left ? left : findNode(root->right, value);
}
template<class T> void printValue(const T& value) { cout << value; }
void printValue(const bool& value) { cout << (value ? "true" : "false"); }
void printValue(const string& value) {
    const char* hex = "0123456789abcdef";
    cout << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') cout << '\\' << c;
        else if (c < 32) cout << "\\u00" << hex[c >> 4] << hex[c & 15];
        else cout << c;
    }
    cout << '"';
}
template<class T> void printValue(const vector<T>& values) {
    cout << '[';
    for (size_t i = 0; i < values.size(); ++i) { if (i) cout << ','; printValue(values[i]); }
    cout << ']';
}
void printValue(ListNode* head) {
    vector<int> values; unordered_set<ListNode*> seen;
    while (head) {
        if (!seen.insert(head).second) throw runtime_error("Unexpected cycle in returned list");
        values.push_back(head->val); head = head->next;
    }
    printValue(values);
}
void printValue(TreeNode* root) {
    vector<string> values; queue<TreeNode*> pending;
    if (root) pending.push(root);
    while (!pending.empty()) {
        auto node = pending.front(); pending.pop();
        values.push_back(node ? to_string(node->val) : "null");
        if (node) { pending.push(node->left); pending.push(node->right); }
    }
    while (!values.empty() && values.back() == "null") values.pop_back();
    cout << '[';
    for (size_t i = 0; i < values.size(); ++i) { if (i) cout << ','; cout << values[i]; }
    cout << ']';
}
void printValue(Node* head) {
    vector<Node*> nodes; unordered_map<Node*, int> indices;
    for (auto p = head; p; p = p->next) { indices[p] = nodes.size(); nodes.push_back(p); }
    cout << '[';
    for (size_t i = 0; i < nodes.size(); ++i) {
        if (i) cout << ',';
        cout << '[' << nodes[i]->val << ',';
        if (nodes[i]->random) cout << indices[nodes[i]->random]; else cout << "null";
        cout << ']';
    }
    cout << ']';
}
'''

CPP_TYPES = {"int": "int", "bool": "bool", "double": "double", "string": "string", "int[]": "vector<int>", "string[]": "vector<string>", "int[][]": "vector<vector<int>>", "char[][]": "vector<vector<char>>", "string[][]": "vector<vector<string>>", "TreeNode": "TreeNode*", "ListNode": "ListNode*", "ListNode[]": "vector<ListNode*>", "Node": "Node*", "void": "void"}
DESIGNS = {
    "LRUCache": {"constructor": ["int"], "get": (["int"], "int"), "put": (["int", "int"], "void")},
    "MinStack": {"constructor": [], "push": (["int"], "void"), "pop": ([], "void"), "top": ([], "int"), "getMin": ([], "int")},
    "MedianFinder": {"constructor": [], "addNum": (["int"], "void"), "findMedian": ([], "double")},
    "Trie": {"constructor": [], "insert": (["string"], "void"), "search": (["string"], "bool"), "startsWith": (["string"], "bool")},
}


def brief(code, language):
    """Remove comments without changing quoted text, operators, or line structure."""
    if language == "python":
        tokens = tokenize.generate_tokens(io.StringIO(code).readline)
        result = tokenize.untokenize(token for token in tokens if token.type != tokenize.COMMENT)
    else:
        result, index = [], 0
        while index < len(code):
            # Raw string delimiters may themselves contain quote/comment characters.
            raw = re.match(r'(?:u8|u|U|L)?R"([^ ()\\\t\r\n]{0,16})\(', code[index:])
            if raw:
                end = code.find(")" + raw.group(1) + '"', index + raw.end())
                end = len(code) if end < 0 else end + len(raw.group(1)) + 2
                result.append(code[index:end])
                index = end
            elif code[index] == "'" and index + 1 < len(code) and code[index + 1].isalnum() and re.search(r"\b(?:0[xX][0-9A-Fa-f']+|0[bB][01']+|[0-9][0-9']*)$", code[:index]):
                # C++14 numeric separators (1'000 or 0xFF'FF) are not quotes.
                result.append(code[index])
                index += 1
            elif code[index] in ('"', "'"):
                quote, start = code[index], index
                index += 1
                while index < len(code):
                    if code[index] == "\\":
                        index += 2
                    elif code[index] == quote:
                        index += 1
                        break
                    else:
                        index += 1
                result.append(code[start:index])
            elif code.startswith("//", index):
                end = code.find("\n", index)
                while end >= 0 and code[index:end].rstrip("\r").endswith("\\"):
                    end = code.find("\n", end + 1)
                result.append("\n" * code[index:end if end >= 0 else len(code)].count("\n"))
                index = len(code) if end < 0 else end
            elif code.startswith("/*", index):
                end = code.find("*/", index + 2)
                end = len(code) if end < 0 else end + 2
                # Keep newlines and a separator so int/**/value stays two tokens.
                result.append(" " + "\n" * code[index:end].count("\n"))
                index = end
            else:
                result.append(code[index])
                index += 1
        result = "".join(result)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in result.splitlines())).strip() + "\n"


def format_arg(value, kind):
    if kind in ("int", "double"):
        return str(value)
    if kind == "bool":
        return "true" if value else "false"
    if kind == "string":
        return json.dumps(value, ensure_ascii=False)
    if kind in ("int[]", "string[]", "ListNode", "TreeNode"):
        return str(len(value)) + "\n" + " ".join(json.dumps(x, ensure_ascii=False) for x in value)
    if kind == "ListNode[]":
        return str(len(value)) + "\n" + "\n".join(format_arg(x, "ListNode") for x in value)
    if kind == "Node":
        return str(len(value)) + "\n" + "\n".join(f"{x[0]} {x[1] if x[1] is not None else -1}" for x in value)
    if kind in ("int[][]", "char[][]"):
        return f"{len(value)} {len(value[0]) if value else 0}\n" + "\n".join(" ".join(str(x) for x in row) for row in value)
    raise ValueError("Unsupported type " + kind)


def format_input(problem, args):
    if problem.get("special") == "design":
        ops, values = args
        return str(len(ops)) + "\n" + "\n".join(op + (" " if value else "") + " ".join(json.dumps(x, ensure_ascii=False) for x in value) for op, value in zip(ops, values)) + "\n"
    chunks = []
    for i, param in enumerate(problem["params"]):
        kind = "int" if problem.get("special") == "lca" and i else param["type"]
        chunks.append(format_arg(args[i], kind))
    if problem.get("special") in ("cycle", "intersection"):
        chunks.extend(str(x) for x in args[len(problem["params"]):])
    return "\n".join(chunks) + "\n"


PY_EXTRA_HELPERS = '''
def read_json_values(line):
    decoder = json.JSONDecoder()
    values = []
    while line.strip():
        value, end = decoder.raw_decode(line.lstrip())
        values.append(value)
        line = line.lstrip()[end:]
    return values

def read_random_list():
    count = int(input())
    pairs = [list(map(int, input().split())) for _ in range(count)]
    nodes = [Node(value) for value, _ in pairs]
    for index, (_, target) in enumerate(pairs):
        if target < -1 or target >= count:
            raise ValueError('random 下标越界')
        nodes[index].next = nodes[index + 1] if index + 1 < count else None
        nodes[index].random = nodes[target] if target >= 0 else None
    return nodes[0] if nodes else None

def tree_values(root):
    queue = deque([root]) if root else deque()
    values = []
    while queue:
        node = queue.popleft()
        values.append(node.val if node else None)
        if node:
            queue.extend([node.left, node.right])
    while values and values[-1] is None:
        values.pop()
    return values

def random_values(head):
    nodes = list_nodes(head)
    indices = {id(node): index for index, node in enumerate(nodes)}
    for node in nodes:
        if node.random is not None and id(node.random) not in indices:
            raise ValueError('副本的 random 不能指向副本链表之外')
    return [[node.val, indices[id(node.random)] if node.random else None] for node in nodes]

def verify_random_copy(original, state, copied):
    original_ids = {id(node) for node in original}
    if any(id(node) in original_ids for node in list_nodes(copied)):
        raise ValueError('必须创建独立的深拷贝，不能返回原链表节点')
    if [(node.val, node.next, node.random) for node in original] != state:
        raise ValueError('复制完成后必须恢复原链表的值和指针')
'''


def _definitions(source):
    return {node.name: ast.get_source_segment(source, node)
            for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


PY_DEFINITIONS = _definitions(PY_NODES + PY_HELPERS + PY_EXTRA_HELPERS)


def _python_read(name, kind):
    """Emit the actual input format directly beside each argument."""
    if kind in ("int", "double", "bool", "string"):
        expression = {"int": "int(input())", "double": "float(input())",
                      "bool": "json.loads(input())", "string": "json.loads(input())"}[kind]
        return [f"{name} = {expression}"]
    if kind == "Node":
        return [f"{name} = read_random_list()"]
    if kind == "ListNode[]":
        return [f"{name}_count = int(input())", f"{name} = []", f"for _ in range({name}_count):"] + [
            "    " + line for line in _python_read(name + "_head", "ListNode")] + [
            f"    {name}.append({name}_head)"]
    if kind in ("int[][]", "char[][]"):
        expression = "list(map(int, input().split()))" if kind == "int[][]" else "input().split()"
        return [f"{name}_rows, {name}_cols = map(int, input().split())", f"{name} = []",
                f"for _ in range({name}_rows):", f"    row = {expression}",
                f"    if len(row) != {name}_cols:", "        raise ValueError('矩阵列数与输入不一致')",
                f"    {name}.append(row)"]
    if kind in ("int[]", "string[]", "ListNode", "TreeNode"):
        expression = "read_json_values(input())" if kind == "string[]" else (
            "[None if value == 'null' else int(value) for value in input().split()]" if kind == "TreeNode"
            else "list(map(int, input().split()))")
        variable = name + "_values" if kind in ("ListNode", "TreeNode") else name
        lines = [f"{name}_count = int(input())", f"{variable} = {expression}",
                 f"if len({variable}) != {name}_count:", "    raise ValueError('元素数量与输入不一致')"]
        if kind in ("ListNode", "TreeNode"):
            lines.append(f"{name} = {'make_list' if kind == 'ListNode' else 'make_tree'}({variable})")
        return lines
    raise ValueError("未知参数类型: " + kind)


def _result_kind(problem):
    return problem["params"][problem.get("mutates", 0)]["type"] if problem["returns"] == "void" else problem["returns"]


def python_main(problem):
    special = problem.get("special")
    if special == "design":
        name = problem["className"]
        return textwrap.dedent(f'''
        def main():
            count = int(input())
            results = []
            instance = None
            for _ in range(count):
                operation, _, arguments = input().partition(' ')
                args = read_json_values(arguments)
                if operation == {name!r}:
                    instance = {name}(*args)
                    results.append(None)
                else:
                    results.append(getattr(instance, operation)(*args))
            print(json.dumps(results, ensure_ascii=False))

        if __name__ == '__main__':
            main()
        ''').strip() + '\n'
    lines = ["def main():"]
    names = [param["name"] for param in problem["params"]]
    for i, param in enumerate(problem["params"]):
        kind = "int" if special == "lca" and i else param["type"]
        lines.extend("    " + line for line in _python_read(param["name"], kind))
    if special == "cycle":
        lines += [f"    nodes = list_nodes({names[0]})", "    pos = int(input())",
                  "    if pos < -1 or pos >= len(nodes):", "        raise ValueError('环入口下标越界')",
                  "    if pos >= 0:", "        nodes[-1].next = nodes[pos]"]
    elif special == "intersection":
        lines += ["    skip_a, skip_b = int(input()), int(input())",
                  f"    nodes_a, nodes_b = list_nodes({names[0]}), list_nodes({names[1]})",
                  "    if 0 <= skip_a < len(nodes_a) and 0 <= skip_b < len(nodes_b):",
                  "        if skip_b == 0:", f"            {names[1]} = nodes_a[skip_a]",
                  "        else:", "            nodes_b[skip_b - 1].next = nodes_a[skip_a]"]
    elif special == "lca":
        lines += [f"    {name} = find_node({names[0]}, {name})" for name in names[1:]]
    elif special == "random-list":
        lines += [f"    original_nodes = list_nodes({names[0]})",
                  "    original_state = [(node.val, node.next, node.random) for node in original_nodes]"]
    lines.append(f"    result = Solution().{problem['method']}({', '.join(names)})")
    if problem["returns"] == "void":
        lines.append(f"    result = {names[problem.get('mutates', 0)]}")
    if special == "cycle" and problem["id"] == 142:
        lines += ["    if result is not None and not any(node is result for node in nodes):",
                  "        raise ValueError('环入口必须是输入链表中的节点')",
                  "    result = next((i for i, node in enumerate(nodes) if node is result), -1)"]
    elif special == "intersection":
        lines += ["    expected_node = nodes_a[skip_a] if 0 <= skip_a < len(nodes_a) and 0 <= skip_b < len(nodes_b) else None",
                  "    if result is not expected_node:", "        raise ValueError('必须返回第一个共享节点本身，无交点返回 None')",
                  "    result = result.val if result is not None else None"]
    elif special == "lca":
        lines += [f"    if result is not None and find_node({names[0]}, result.val) is not result:",
                  "        raise ValueError('祖先必须是输入树中的节点')"]
        lines.append("    result = result.val if result is not None else None")
    elif _result_kind(problem) == "ListNode":
        lines.append("    result = [node.val for node in list_nodes(result)]")
    elif _result_kind(problem) == "TreeNode":
        lines.append("    result = tree_values(result)")
    elif _result_kind(problem) == "Node":
        if special == "random-list":
            lines.append("    verify_random_copy(original_nodes, original_state, result)")
        lines.append("    result = random_values(result)")
    lines += ["    print(json.dumps(result, ensure_ascii=False))", "", "if __name__ == '__main__':", "    main()", ""]
    return "\n".join(lines)


def cpp_main(problem):
    special = problem.get("special")
    lines = ["int main() {", "    ios::sync_with_stdio(false);", "    cin.tie(nullptr);"]
    if problem["returns"] == "double" or problem.get("className") == "MedianFinder":
        lines.append("    cout << setprecision(15);")
    if special == "design":
        name = problem["className"]
        lines += [f"    {name}* instance = nullptr;", "    int count; cin >> count;", "    cout << '[';", "    for (int i = 0; i < count; ++i) {", "        if (i) cout << ',';", "        string operation; cin >> operation;"]
        for method, spec in DESIGNS[name].items():
            types, returns = (spec, "void") if method == "constructor" else spec
            operation = name if method == "constructor" else method
            lines.append(f'        if (operation == "{operation}") {{')
            for i, kind in enumerate(types):
                lines.append(f"            {CPP_TYPES[kind]} arg{i}; readValue(arg{i});")
            args = ", ".join(f"arg{i}" for i in range(len(types)))
            if method == "constructor":
                lines.append(f'            instance = new {name}({args}); cout << "null";')
            elif returns == "void":
                lines.append(f'            instance->{method}({args}); cout << "null";')
            else:
                lines.append(f"            printValue(instance->{method}({args}));")
            lines.append("        }")
        lines += ["    }", '    cout << "]\\n";', "    return 0;", "}"]
        return "\n".join(lines)
    names = [p["name"] for p in problem["params"]]
    for i, param in enumerate(problem["params"]):
        kind = "int" if special == "lca" and i else param["type"]
        name = param["name"] + ("Value" if special == "lca" and i else "")
        reader = "readMatrix" if kind in ("int[][]", "char[][]") else "readValue"
        lines.append(f"    {CPP_TYPES[kind]} {name}; {reader}({name});")
    if special == "cycle":
        lines += [f"    vector<ListNode*> nodes; for (auto p = {names[0]}; p; p = p->next) nodes.push_back(p);", "    int pos; cin >> pos;",
                  '    if (pos < -1 || pos >= (int)nodes.size()) throw invalid_argument("Cycle index out of bounds");',
                  "    if (pos >= 0) nodes.back()->next = nodes.at(pos);"]
    elif special == "intersection":
        lines += ["    int skipA, skipB; cin >> skipA >> skipB;", f"    vector<ListNode*> nodesA, nodesB; for (auto p = {names[0]}; p; p = p->next) nodesA.push_back(p);", f"    for (auto p = {names[1]}; p; p = p->next) nodesB.push_back(p);", "    if (skipA >= 0 && skipB >= 0 && skipA < (int)nodesA.size() && skipB < (int)nodesB.size()) {", f"        if (skipB == 0) {names[1]} = nodesA[skipA]; else nodesB[skipB - 1]->next = nodesA[skipA];", "    }"]
    elif special == "lca":
        lines += [f"    TreeNode* {name} = findNode({names[0]}, {name}Value);" for name in names[1:]]
    elif special == "random-list":
        lines += ["    vector<Node*> originals, originalNext, originalRandom;", "    vector<int> originalValues;",
                  f"    for (Node* node = {names[0]}; node; node = node->next) {{",
                  "        originals.push_back(node); originalNext.push_back(node->next);",
                  "        originalRandom.push_back(node->random); originalValues.push_back(node->val);", "    }"]
    call = f"Solution().{problem['method']}({', '.join(names)})"
    if problem["returns"] == "void":
        lines += [f"    {call};", f"    auto result = {names[problem.get('mutates', 0)]};"]
    else:
        lines.append(f"    auto result = {call};")
    if special == "cycle" and problem["id"] == 142:
        lines += ["    int index = -1;", "    for (int i = 0; i < (int)nodes.size(); ++i) if (nodes[i] == result) index = i;",
                  '    if (result && index < 0) throw runtime_error("Return an original list node");', "    printValue(index);"]
    elif special == "intersection":
        lines += ["    ListNode* expectedNode = skipA >= 0 && skipB >= 0 && skipA < (int)nodesA.size() && skipB < (int)nodesB.size() ? nodesA[skipA] : nullptr;",
                  '    if (result != expectedNode) throw runtime_error("Return the shared node itself, or nullptr");',
                  '    if (result) printValue(result->val); else cout << "null";']
    elif special == "lca":
        lines.append(f'    if (result && findNode({names[0]}, result->val) != result) throw runtime_error("Return an original tree node");')
        lines.append('    if (result) printValue(result->val); else cout << "null";')
    elif special == "random-list":
        lines += ["    unordered_set<Node*> originalSet(originals.begin(), originals.end()), copiedSet;",
                  "    for (Node* node = result; node; node = node->next) {",
                  "        if (originalSet.count(node) || !copiedSet.insert(node).second)",
                  '            throw runtime_error("The copied list must contain new, acyclic nodes");', "    }",
                  "    for (Node* node : copiedSet)",
                  "        if (node->random && !copiedSet.count(node->random))",
                  '            throw runtime_error("Random pointers must stay inside the copied list");',
                  "    for (size_t i = 0; i < originals.size(); ++i)",
                  "        if (originals[i]->val != originalValues[i] || originals[i]->next != originalNext[i] || originals[i]->random != originalRandom[i])",
                  '            throw runtime_error("Restore the original list after copying");',
                  "    printValue(result);"]
    else:
        lines.append("    printValue(result);")
    lines += ['    cout << "\\n";', "    return 0;", "}", ""]
    return "\n".join(lines)


def starter(problem, language):
    if language == "python":
        tree = ast.parse(problem["python"])
        name = problem.get("className", "Solution")
        klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
        functions = []
        for node in klass.body:
            if isinstance(node, ast.FunctionDef) and (node.name == problem["method"] or (problem.get("special") == "design" and (not node.name.startswith("_") or node.name == "__init__"))):
                item = copy.deepcopy(node)
                item.body = [ast.Raise(exc=ast.Call(func=ast.Name(id="NotImplementedError", ctx=ast.Load()), args=[ast.Constant(value="请写下你的思路与实现")], keywords=[]), cause=None)]
                functions.append(item)
        newclass = ast.ClassDef(name=name, bases=[], keywords=[], body=functions, decorator_list=[])
        return "from typing import *\n\n" + ast.unparse(ast.fix_missing_locations(newclass)) + "\n"
    if problem.get("special") == "design":
        name = problem["className"]
        lines = [f"class {name} {{", "public:"]
        for method, spec in DESIGNS[name].items():
            types, ret = (spec, "void") if method == "constructor" else spec
            args = ", ".join(CPP_TYPES[t] + f" arg{i}" for i, t in enumerate(types))
            signature = name if method == "constructor" else CPP_TYPES[ret] + " " + method
            lines += [f"    {signature}({args}) {{", '        throw runtime_error("请完成实现");', "    }"]
        return "\n".join(lines + ["};", ""])
    args = ", ".join(CPP_TYPES[p["type"]] + ("&" if p["type"].endswith("[]") or p["type"] == "string" else "") + " " + p["name"] for p in problem["params"])
    return f'class Solution {{\npublic:\n    {CPP_TYPES[problem["returns"]]} {problem["method"]}({args}) {{\n        // 从这里开始实现\n        throw runtime_error("请完成实现");\n    }}\n}};\n'


def _python_names(source):
    try:
        return {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    except SyntaxError:
        return set(re.findall(r"\b[A-Za-z_]\w*\b", source))


def _node_kinds(problem):
    kinds = {param["type"].removesuffix("[]") for param in problem["params"]} | {problem["returns"]}
    return kinds & {"ListNode", "TreeNode", "Node"}


def _python_program(problem, source):
    main = python_main(problem)
    try:
        source_tree = ast.parse(source)
        # Future imports must precede generated imports and node definitions.
        futures = [node for node in source_tree.body if isinstance(node, ast.ImportFrom) and node.module == "__future__"]
        future_lines = {line for node in futures for line in range(node.lineno, node.end_lineno + 1)}
        future_code = "\n".join(ast.get_source_segment(source, node) for node in futures)
        source = "\n".join(line for index, line in enumerate(source.splitlines(), 1) if index not in future_lines)
        defined = {node.name for node in source_tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
        imported = {alias.asname or alias.name.split('.')[0]
                    for node in source_tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                    for alias in node.names}
    except SyntaxError:
        # Preserve invalid user code so the child process returns a useful SyntaxError.
        future_code, defined, imported = "", set(), set()
    selected = set()
    blocked_nodes = {"ListNode", "TreeNode", "Node"} - _node_kinds(problem)
    pending = (_python_names(main + "\n" + source) & PY_DEFINITIONS.keys()) - blocked_nodes
    while pending:
        name = pending.pop()
        if name in selected or name in defined:
            continue
        selected.add(name)
        references = {node.id for node in ast.walk(ast.parse(PY_DEFINITIONS[name])) if isinstance(node, ast.Name)}
        pending.update((references & PY_DEFINITIONS.keys()) - selected - defined - blocked_nodes)
    support = "\n\n".join(definition for name, definition in PY_DEFINITIONS.items() if name in selected)
    needed = _python_names(support + "\n" + source + "\n" + main) - imported
    imports = ["import json"]
    for module in ("heapq", "bisect", "math", "random", "sys", "typing", "collections"):
        if module in needed:
            imports.append("import " + module)
    for module, candidates in {
        "typing": {"List", "Optional", "Tuple", "Dict", "Set", "Any", "Deque", "DefaultDict"},
        "collections": {"deque", "Counter", "defaultdict", "OrderedDict"},
        "heapq": {"heappush", "heappop", "heapify", "heappushpop", "heapreplace"},
        "bisect": {"bisect_left", "bisect_right"},
    }.items():
        names = sorted(needed & candidates)
        if names:
            imports.append(f"from {module} import {', '.join(names)}")
    return "\n\n".join(section.strip() for section in (future_code, "\n".join(imports), support, source, main) if section.strip()) + "\n"


def _cpp_sections(source, markers):
    offsets = [(name, source.index(marker)) for name, marker in markers]
    return {name: source[start:offsets[index + 1][1] if index + 1 < len(offsets) else len(source)].strip()
            for index, (name, start) in enumerate(offsets)}


CPP_DEFINITIONS = _cpp_sections(CPP_HELPERS, [
    ("read_scalar", "template<class T> void readValue(T&"),
    ("read_string", "void readValue(string&"),
    ("read_vector", "template<class T> void readValue(vector<T>&"),
    ("read_matrix", "template<class T> void readMatrix"),
    ("read_list", "void readValue(ListNode*&"),
    ("read_tree", "void readValue(TreeNode*&"),
    ("read_lists", "void readValue(vector<ListNode*>&"),
    ("read_random", "void readValue(Node*&"),
    ("find_node", "TreeNode* findNode"),
    ("print_scalar", "template<class T> void printValue(const T&"),
    ("print_bool", "void printValue(const bool&"),
    ("print_string", "void printValue(const string&"),
    ("print_vector", "template<class T> void printValue(const vector<T>&"),
    ("print_list", "void printValue(ListNode*"),
    ("print_tree", "void printValue(TreeNode*"),
    ("print_random", "void printValue(Node*"),
])
CPP_NODE_DEFINITIONS = _cpp_sections(CPP_NODES, [
    ("ListNode", "struct ListNode"), ("TreeNode", "struct TreeNode"), ("Node", "class Node")])

CPP_HEADERS = {
    "algorithm": r"\b(sort|stable_sort|reverse|swap|min|max|minmax|lower_bound|upper_bound|binary_search|nth_element|next_permutation|fill|copy|all_of|any_of|find|remove|unique)\b",
    "array": r"\barray\b", "bitset": r"\bbitset\b",
    "climits": r"\b(INT_MIN|INT_MAX|LLONG_MIN|LLONG_MAX|LONG_MIN|LONG_MAX)\b",
    "cmath": r"\b(sqrt|pow|floor|ceil|fabs|abs|log|log2|round)\b",
    "cctype": r"\b(isdigit|isalpha|isalnum|isspace|islower|isupper|tolower|toupper)\b",
    "cstdint": r"\b(u?int(?:8|16|32|64)_t)\b", "cstdlib": r"\b(rand|srand|abs|llabs)\b",
    "cstring": r"\b(memset|memcpy|strlen|strcmp)\b",
    "deque": r"\bdeque\b", "functional": r"\b(function|greater|less|hash)\b",
    "iomanip": r"\b(quoted|setprecision|setw|setfill)\b", "iostream": r"\b(cin|cout|cerr|ios)\b",
    "limits": r"\bnumeric_limits\b", "list": r"\blist\b", "map": r"\b(multimap|map)\b",
    "numeric": r"\b(accumulate|iota|gcd|lcm|partial_sum)\b", "queue": r"\b(priority_queue|queue)\b",
    "random": r"\b(mt19937|mt19937_64|random_device|uniform_int_distribution)\b",
    "set": r"\b(multiset|set)\b", "sstream": r"\b(stringstream|istringstream|ostringstream)\b",
    "stack": r"\bstack\b", "stdexcept": r"\b(runtime_error|invalid_argument|out_of_range|logic_error)\b",
    "string": r"\b(string|stoi|stoll|stod|to_string)\b",
    "unordered_map": r"\bunordered_(?:multi)?map\b", "unordered_set": r"\bunordered_(?:multi)?set\b",
    "utility": r"\b(pair|make_pair|move|forward|swap)\b", "vector": r"\bvector\b",
    "tuple": r"\b(tuple|make_tuple)\b|\bget\s*<", "memory": r"\b(unique_ptr|shared_ptr|make_unique|make_shared)\b",
}


def _cpp_program(problem, source):
    special = problem.get("special")
    readers = {"int": {"read_scalar"}, "double": {"read_scalar"}, "bool": {"read_scalar"},
               "string": {"read_string"}, "int[]": {"read_scalar", "read_vector"},
               "string[]": {"read_string", "read_vector"}, "int[][]": {"read_scalar", "read_matrix"},
               "char[][]": {"read_scalar", "read_matrix"}, "ListNode": {"read_list"},
               "ListNode[]": {"read_list", "read_lists"}, "TreeNode": {"read_tree"}, "Node": {"read_random"}}
    printers = {"int": {"print_scalar"}, "double": {"print_scalar"}, "bool": {"print_bool"},
                "string": {"print_string"}, "int[]": {"print_scalar", "print_vector"},
                "int[][]": {"print_scalar", "print_vector"}, "string[]": {"print_string", "print_vector"},
                "string[][]": {"print_string", "print_vector"}, "char[][]": {"print_string", "print_vector", "print_scalar"},
                "ListNode": {"print_scalar", "print_vector", "print_list"},
                "TreeNode": {"print_tree"}, "Node": {"print_random"}}
    selected = set()
    if special == "design":
        for method, spec in DESIGNS[problem["className"]].items():
            inputs, output = (spec, "void") if method == "constructor" else spec
            for kind in inputs:
                selected.update(readers[kind])
            if output != "void":
                selected.update(printers[output])
    else:
        for index, param in enumerate(problem["params"]):
            selected.update(readers["int" if special == "lca" and index else param["type"]])
        output = "int" if special in ("intersection", "lca") or (special == "cycle" and problem["id"] == 142) else _result_kind(problem)
        selected.update(printers[output])
        if special == "lca":
            selected.add("find_node")
    support = "\n\n".join(value for key, value in CPP_DEFINITIONS.items() if key in selected)
    main = cpp_main(problem)
    body = "\n\n".join((support, source, main))
    nodes = "\n\n".join(value for name, value in CPP_NODE_DEFINITIONS.items() if name in _node_kinds(problem))
    body = "\n\n".join((nodes, body)).strip()
    # Standard headers keep downloaded programs portable beyond GNU-only toolchains.
    headers = "\n".join(f"#include <{header}>" for header, pattern in CPP_HEADERS.items() if re.search(pattern, body))
    return headers + "\nusing namespace std;\n\n" + body + "\n"


def program(problem, language, source):
    if language == "python":
        return _python_program(problem, source)
    return _cpp_program(problem, source)


def describe_input(problem):
    if problem.get("special") == "design":
        return ["第一行输入操作次数。", "接下来每行：操作名及其参数，以空格分隔；字符串用双引号包裹。", "第一条操作为类名（构造函数）。输出 JSON 数组，void 操作用 null 表示。"]
    descriptions = {"int": "一行整数", "double": "一行浮点数", "string": "一行双引号包裹的字符串（空串写作 \"\"）", "int[]": "先输入长度，再输入一行空格分隔的整数（空数组仍保留空行）", "string[]": "先输入长度，再输入一行双引号包裹、空格分隔的字符串", "int[][]": "先输入行数和列数，再逐行输入整数", "char[][]": "先输入行数和列数，再逐行输入空格分隔的字符", "ListNode": "先输入节点数，再输入一行节点值", "TreeNode": "先输入层序序列长度，再输入一行节点值，空节点写 null", "ListNode[]": "先输入链表个数，每条链表依次输入节点数及一行节点值", "Node": "先输入节点数，每行输入节点值和 random 下标（空指针用 -1）"}
    result = []
    for i, p in enumerate(problem["params"]):
        kind = "int" if problem.get("special") == "lca" and i else p["type"]
        result.append(p["name"] + "：" + descriptions[kind] + "。")
    if problem.get("special") == "cycle":
        result.append("最后一行输入环入口下标 pos，无环写 -1。")
    if problem.get("special") == "intersection":
        result.append("最后两行分别输入 skipA、skipB（公共尾部起点），无交点时均写 -1。")
    result.append("输出一行 JSON 值；链表输出节点数组，二叉树输出层序数组。")
    return result


def enrich(problem):
    result = dict(problem)
    result["solutions"] = {}
    result["templates"] = {}
    for language, field in (("python", "python"), ("cpp", "cpp")):
        annotated = problem[field].strip() + "\n"
        concise = brief(annotated, language)
        template = starter(problem, language)
        result["solutions"][language] = {
            "leetcode": {"brief": concise, "annotated": annotated},
            "acm": {"brief": brief(program(problem, language, concise), language), "annotated": program(problem, language, annotated)},
        }
        result["templates"][language] = {"leetcode": template, "acm": program(problem, language, template)}
    result["examples"] = [{**example, "stdin": format_input(problem, example["input"])} for example in problem["examples"]]
    result["inputGuide"] = describe_input(problem)
    result.pop("python", None)
    result.pop("cpp", None)
    return result
