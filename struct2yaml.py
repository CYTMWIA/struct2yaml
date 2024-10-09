import argparse

import tree_sitter
import tree_sitter_c
from yaml import dump

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper


def yaml_dumps(obj):
    return dump(obj, Dumper=Dumper)


LANG_C = tree_sitter.Language(tree_sitter_c.language())
parser = tree_sitter.Parser(LANG_C)


def print_pretty_tree(node: tree_sitter.Node, depth=0):
    tabs = "\t" * depth
    line = f"{tabs}type: {node.type}"
    if node.child_count == 0:
        line += f", text: {node.text}"
    if node.is_named:
        print(line)

    for child in node.children:
        print_pretty_tree(child, depth=depth + 1)


def query_global_varibale_declarations(node: tree_sitter.Node):
    query = LANG_C.query(
        """
        (translation_unit
            (declaration)@declaration)
        """
    )
    matches = query.matches(node)
    return [m[1]["declaration"][0] for m in matches]


def query_variable_name(node: tree_sitter.Node):
    query = LANG_C.query(
        """
        (identifier)@identifier
        """
    )
    matches = query.matches(node)
    if len(matches) == 0:
        print("identifier not found in node")
        return None
    return matches[0][1]["identifier"][0].text


def query_named_struct_specifiers(node: tree_sitter.Node):
    query = LANG_C.query(
        """
        (struct_specifier
            (type_identifier)@identifier
            (field_declaration_list)@declaration_list
        )@specifier
        """
    )
    matches = query.matches(node)
    return [
        {
            "specifier": m[1]["specifier"][0],
            "identifier": m[1]["identifier"][0],
            "declaration_list": m[1]["declaration_list"][0],
        }
        for m in matches
    ]


def read_files(paths: list[str]):
    res = []
    for path in paths:
        with open(path, "rb") as f:
            res.append(f.read())
    return res


def merge_files_content(content_list: list[bytes]):
    return b"\n".join(content_list)


struct_specs: list[dict[str, tree_sitter.Node]] = []


def find_struct_by_name(name: str | bytes):
    if isinstance(name, str):
        name = name.encode()
    for spec in struct_specs:
        if spec["identifier"].text == name:
            return spec
    return None


def struct2dict(spec: dict[str, tree_sitter.Node]):
    res = {}
    for child in spec["declaration_list"].named_children:
        if child.type != "field_declaration":
            continue
        field_declaration = child
        field_type = field_declaration.named_children[0]
        place_holder = ""
        if field_type.type == "struct_specifier":
            struct_name = field_type.named_children[0].text
            place_holder = struct2dict(find_struct_by_name(struct_name))
        for child2 in field_declaration.named_children[1:]:
            if child2.type != "field_identifier":
                continue
            res[child2.text.decode()] = place_holder
    return res


def main(inputs: list[str], output_type: str, identifier: str | None = None):
    code = merge_files_content(read_files(inputs))
    tree = parser.parse(code)
    root = tree.root_node
    if output_type == "ast":
        print_pretty_tree(root)
        return 0

    # global struct_specs, sturct_names
    # gvars = query_global_varibale_declarations(root)
    # var_names = [query_variable_name(gv) for gv in gvars]
    # struct_specs = query_named_struct_specifiers(root)

    # st = find_struct_by_name(target_struct)
    # if st is None:
    #     print("Target struct not exists")
    #     return -1

    # d = struct2dict(st)
    # print(yaml_dumps(d), end="")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Convert struct to yaml or something else."
    )

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        nargs="+",
        required=True,
        help="input source files",
    )

    parser.add_argument("--identifier", type=str, default=None, help="identifier name")

    parser.add_argument(
        "--output_type",
        type=str,
        required=True,
        choices=["ast", "yaml"],
        help="output type",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    ret = main(
        inputs=args.input,
        output_type=args.output_type,
        identifier=args.identifier,
    )
    exit(ret)
