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
    indents = "    " * depth

    line = f"{indents}<{node.type}"
    if node.child_count == 0:
        line += f" text={node.text}"
    line += ">"
    print(line)

    for idx, child in enumerate(node.children):
        if not child.is_named:
            continue

        field_name = node.field_name_for_child(idx)
        if field_name is not None:
            print(f"{indents}  {field_name}:")

        print_pretty_tree(child, depth=depth + 1)


def query_match(node: tree_sitter.Node, query: str):
    q = LANG_C.query(query)
    return q.matches(node)


def read_files(paths: list[str]):
    res = []
    for path in paths:
        with open(path, "rb") as f:
            res.append(f.read())
    return res


def merge_files_content(content_list: list[bytes]):
    return b"\n".join(content_list)


def str_and_bytes(s_or_b: str | bytes):
    if isinstance(s_or_b, str):
        return s_or_b, s_or_b.encode()
    else:
        return s_or_b.decode(), s_or_b


def _query_underlying_type_typedef(node: tree_sitter.Node, id_s: str):
    matches = query_match(
        node,
        f"""
        (type_definition
            (type_identifier)@identifier (#eq? @identifier "{id_s}")
        )@definition
        """,
    )
    if len(matches):
        definition = matches[0][1]["definition"][0]
        type_ = definition.child_by_field_name("type")
        if type_.type == "struct_specifier":
            struct_body = type_.child_by_field_name("body")
            if struct_body is None:
                struct_name = type_.child_by_field_name("name").text
                return query_underlying_type(node, struct_name)
            else:
                return "struct", type_
        elif type_.type == "enum_specifier":
            # print("enum_specifier not supported")
            return "enum", None
        elif type_.type == "union_specifier":
            print("union_specifier not supported")
            return None, None
        else:
            # print("unknown type")
            return type_.text.decode(), None
    return None, None


def _query_underlying_type_struct(node: tree_sitter.Node, id_s: str):
    matches = query_match(
        node,
        f"""
        (struct_specifier
            (type_identifier)@identifier (#eq? @identifier "{id_s}")
            (field_declaration_list)@list
        )@specifier
        """,
    )
    if len(matches):
        return "struct", matches[0][1]["specifier"][0]
    return None, None


def query_underlying_type(node: tree_sitter.Node, identifier: str | bytes):
    id_s, id_b = str_and_bytes(identifier)

    parts = id_s.split()
    if len(parts) == 1:
        id_ = parts[0]
        for func in [
            _query_underlying_type_typedef,
            _query_underlying_type_struct,
        ]:
            u, d = func(node, id_)
            if u is not None:
                return u, d
    elif len(parts) == 2:
        spec, id_ = parts
        func = {"struct": _query_underlying_type_struct}.get(spec, None)
        if func is None:
            print("unknown specifier", spec)
        else:
            u, d = func(node, id_)
            if u is not None:
                return u, d
    else:
        print("cannot parse identifier:", id_s)

    # print("query_underlying_type failed:", id_s)
    return id_s, None


def struct_specifier2dict(root: tree_sitter.Node, struct_specifier: tree_sitter.Node):
    body = struct_specifier.child_by_field_name("body")
    if body is None:
        name = struct_specifier.child_by_field_name("name")
        under, detail = query_underlying_type(root, name.text)
        if under == "struct":
            return struct_specifier2dict(root, detail)
        else:
            return {}
    res = {}
    for child in body.named_children:
        if child.type != "field_declaration":
            continue
        field_declaration = child
        field_type = field_declaration.child_by_field_name("type")
        place_holder = field_type.text.decode()
        if field_type.type == "struct_specifier":
            place_holder = struct_specifier2dict(root, field_type)
        for child2 in field_declaration.named_children[1:]:
            if child2.type not in [  # _field_declarator
                "array_declarator",
                "attributed_declarator",
                "field_identifier",
                "function_declarator",
                "parenthesized_declarator",
                "pointer_declarator",
            ]:
                continue
            res[child2.text.decode()] = place_holder
    return res


def struct_specifier_body2yaml_cpp(
    root: tree_sitter.Node,
    body: tree_sitter.Node,
):
    encode = []
    decode = []
    for field_declaration in body.named_children:
        if field_declaration.type != "field_declaration":
            continue

        type_node = field_declaration.child_by_field_name("type")
        data_type = type_node.text.decode()
        if type_node.type == "struct_specifier":
            named = type_node.child_by_field_name("name") is not None
            if named:
                struct_specifier2yaml_cpp(root, type_node)
            else:
                print(f"Anonymous struct is not supported: {data_type}")
                # struct_specifier_body2yaml_cpp(root, )
                continue
        elif (
            type_node.type == "enum_specifier"
            or query_underlying_type(root, data_type)[0] == "enum"
        ):
            data_type = "int"
        elif type_node.type == "union_specifier":
            print(f"Union is not supported: {data_type}")
            continue

        for field_node in field_declaration.named_children[1:]:
            if field_node.type == "array_declarator":
                declarator = field_node.child_by_field_name("declarator")
                field_name = declarator.text.decode()
                size_node = field_node.child_by_field_name("size")
                size_s = size_node.text.decode()
                node_var = f'node["{field_name}"]'
                encode += [
                    f"for (i=0; i<({size_s}); i++) {node_var}.push_back(rhs.{field_name}[i]);",
                ]
                decode += [
                    f"if ({node_var})",
                    "{",
                    f"    auto vec = {node_var}.as<std::vector<{data_type}>>();",
                    f"    int asize = {size_s};",
                    "    int csize = std::min(asize, vec.size());",
                    f"    for (i=0; i<csize; i++) rhs.{field_name}[i] = vec[i];",
                    "}",
                ]
            elif field_node.type == "pointer_declarator":
                declarator = field_node.child_by_field_name("declarator")
                field_name = declarator.text.decode()
                node_var = f'node["{field_name}"]'
                encode += [
                    f"if (rhs.{field_name}) {node_var} = *(rhs.{field_name});",
                ]
                decode += [
                    f"if ({node_var})",
                    "{",
                    f"    rhs.{field_name} = ({data_type}*)malloc(sizeof({data_type}));",
                    f"    *(rhs.{field_name}) = {node_var}.as<{data_type}>();",
                    "}",
                ]
            elif field_node.type == "function_declarator":
                print("field type is function_declarator, which is not supported")
                continue
            elif field_node.type in [
                "attributed_declarator",
                "field_identifier",
                "parenthesized_declarator",
                "pointer_declarator",
            ]:
                field_name = field_node.text.decode()
                node_var = f'node["{field_name}"]'
                encode += [f"{node_var} = rhs.{field_name};"]
                decode += [
                    f"if ({node_var}) rhs.{field_name} = {node_var}.as<{data_type}>();"
                ]
    return encode, decode


def struct_specifier2yaml_cpp(
    root: tree_sitter.Node,
    struct_specifier: tree_sitter.Node,
    name: str | None = None,  # useful for typedef struct
):
    if name is None:
        name_node = struct_specifier.child_by_field_name("name")
        if name_node is None:
            print("Anonymous struct is not allowed")
            return None
        name = name_node.text.decode()

    body_node = struct_specifier.child_by_field_name("body")
    if body_node is None:
        under, detail = query_underlying_type(root, name)
        if under == "struct":
            return struct_specifier2yaml_cpp(root, detail)
        else:
            return None

    res = struct_specifier_body2yaml_cpp(root, body_node)
    if res is None:
        print("Convert to yaml-cpp failed")
        return None
    encode, decode = res

    # composite
    res = [
        "template<>",
        f"struct convert<{name}>",
        "{",
        f"  static Node encode(const {name}& rhs)",
        "  {",
        "    Node node;",
        "\n".join(["    " + line for line in encode]),
        "    return node;",
        "  }",
        f"  static bool decode(const Node& node, {name}& rhs)",
        "  {",
        "\n".join(["    " + line for line in decode]),
        "    return true;",
        "  }",
        "};",
    ]
    print("\n".join(res))
    return None


def struct2dict(root: tree_sitter.Node, identifier: str):
    under, detail = query_underlying_type(root, identifier)
    if under != "struct":
        print("identifier is", under)
        return {}
    return struct_specifier2dict(root, detail)


def struct2yaml_cpp(root: tree_sitter.Node, identifier: str):
    under, detail = query_underlying_type(root, identifier)
    if under != "struct":
        print("identifier is", under)
        return {}
    return struct_specifier2yaml_cpp(root, detail, identifier)


def main(inputs: list[str], output_type: str, identifier: str | None = None):
    code = merge_files_content(read_files(inputs))
    tree = parser.parse(code)
    root = tree.root_node
    if output_type == "ast":
        print_pretty_tree(root)
        return 0

    if output_type == "yaml":
        if identifier is None:
            print("identifier cannot be None")
            return -1
        d = struct2dict(root, identifier)
        print(yaml_dumps(d), end="")
        return 0

    if output_type == "yaml-cpp":
        if identifier is None:
            print("identifier cannot be None")
            return -1
        struct2yaml_cpp(root, identifier)
        # print(code)


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
        choices=["ast", "yaml", "yaml-cpp"],
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
