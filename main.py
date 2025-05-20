import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.etree.ElementTree import Element


#对一个类或文件的主体进行处理,输出元素为同级语句或代码段的列表
def divise(text):
    result = []
    stack = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if not stack:
                if start != -1:
                    result.append(text[start:i])
                start = i
            stack += 1
        elif ch == '}':
            stack -= 1
            if not stack:
                result.append(text[start:i+1])
                start = -1
        elif ch == ";":
            if not stack:
                if start != -1:
                    result.append(text[start:i + 1])
                start = i + 1
        else:
            if start == -1:
                start = i
    if start != -1:
        result.append(text[start:])
    return [word.strip() for word in result if word.strip()]

# 根据给定的文件路径将文件读取,并去除注释,包名和导包语句,然后将全文展成一行并调整空隙,最后分割
def prehandle(thepath):
    content = thepath.read_text(encoding="utf-8")
    content = content.split("\n")
    t = 0
    while t < len(content):
        content[t] = content[t].split("//")[0].strip()
        content[t] = content[t].split("import")[0].strip()
        content[t] = content[t].split("package")[0].strip()
        if content[t].startswith("/*") or content[t].startswith("/**"):
            for i in range(t,len(content)):
                if content[i].strip().endswith("*/"):
                    content[i] = ""
                    t = i+1
                    break
                content[i] = ""
        t += 1
    content = " ".join(content)
    content = content.split(" ")
    content = [x for x in content if x]
    return divise(" ".join(content))

# 处理定义语句中的泛参,将语句分割为由"<...>"和剩余单词组成的列表(已去除",")
def handle_def(text):
    result = []
    stack = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '<':
            if not stack:
                if start != -1:
                    result.append(text[start:i])
                start = i
            stack += 1
        elif ch == '>':
            stack -= 1
            if not stack:
                result.append(text[start:i+1])
                start = -1
        elif ch == ",":
            if not stack:
                if start != -1:
                    result.append(text[start:i])
                start = i + 1
        else:
            if start == -1:
                start = i
    if start != -1:
        result.append(text[start:])
    words = []
    for seg in result:
        if seg[0] == "<":
            words.append(seg)
        else:
            words += seg.split(" ")
    return [word.strip() for word in words if word.strip()]

# 判断一个字符串是否为"{...}"类型(即is code segment)
def iscs(word):
    if (word[0] == "{") and (word[-1] == "}"):
        return True
    return False

# 判断一个字符串是否为"<...>"类型(即is type params)
def istp(word):
    if (word[0] == "<") and (word[-1] == ">") :
        return True
    return False

# 以下四个是因为其被高频使用
def node(arglist):
    return Element("node",arglist)

def nod(text):
    return node({"TEXT":text})

def fnod(text):
    return node({"TEXT": text,"FOLDED":"true"})

def concat(parentname,name):
    if parentname:
        return parentname + "." +name
    else:
        return name

# 处理函数输入及record类组件
def handle_input(inputtext,name):
    input_node = fnod(name)
    input_list = []
    stack = 0
    pointer = 0
    for index, ch in enumerate(inputtext):
        if ch == "<":
            stack += 1
        elif ch == ">":
            stack -= 1
        elif ch == "," and stack == 0:
            input_list.append(inputtext[pointer:index].strip())
            pointer = index + 1
    input_list.append(inputtext[pointer:].strip())
    for input_item in input_list:
        words = handle_def(input_item)
        if istp(words[-2]):
            input_node.append(nod("".join(words[-3:-1])))
        else:
            input_node.append(nod(words[-2]))
    return input_node

# 对类中的方法和属性进行处理
def handle_func(functext):
    inputtext = None
    stack = 1
    for i in range(2,len(functext)):
        current = functext[len(functext)-i]
        if current == ")":
            stack += 1
        elif current == "(":
            stack -= 1
            if stack == 0:
                inputtext = functext[len(functext)-i+1:-1]
                functext = functext[:len(functext)-i]
                break
    words = handle_def(functext)
    words = [word for word in words if word[0] != "@"]
    func_name = words[-1]
    del words[-1]
    type_node = None
    if len(words):
        for i in range(len(words)):
            if words[i] not in ["public","default","protected","private","abstract","final","static","synchronized","native","strictfp"]:
                func_name = " ".join(words[:i])+" "+func_name
                del words[:i]
                break
        if istp(words[0]):
            tppms = words[0][1:-1].split(",")
            type_node = fnod("typeparams")
            for tppm in tppms:
                type_node.append(nod(tppm.strip().split(" ")[0]))
            del words[0]
    func_node = fnod(func_name)
    if type_node is not None:
        func_node.append(type_node)
    if len(words):
        output_node = fnod("output")
        output_node.append(nod("".join(words)))
        func_node.append(output_node)
    if inputtext:
        func_node.append(handle_input(inputtext,"input"))
    return func_node

def handle_param(paramtext):
    paramtext = paramtext[:-1].split("=")[0].strip()
    paramtext = " ".join([word for word in paramtext.split(" ") if not word.startswith("@")]).strip()
    return nod(paramtext)

# 对一个类的定义部分进行处理,得到一个可以描述泛参,输入和输出的node
def handle_class_des(description,parentnode = None):
    class_type = "C"
    words = handle_def(description)
    is_record = False
    pos_class = None
    field_node = None
    for word in words:
        if not istp(word) and "(" in word:
            is_record = True
            break
    if is_record:
        stack = 0
        start_pos = None
        for i,ch in enumerate(description):
            if ch == "<":
                stack += 1
            elif ch == ">":
                stack -= 1
            elif ch == "(":
                if start_pos or stack:
                    stack += 1
                else:
                    start_pos = i
            elif ch == ")":
                if stack:
                    stack -= 1
                else:
                    field_node = handle_input(description[start_pos+1:i],"field")
                    description = description[:start_pos]+description[i+1:]
                    words = handle_def(description)
    if "class" in words:
        pos_class = words.index("class")
    elif "enum" in words:
        class_type = "E"
        pos_class = words.index("enum")
    elif "record" in words:
        class_type = "R"
        pos_class = words.index("record")
    elif "interface" in words:
        class_type = "I"
        pos_class = words.index("interface")
    if "static" in words[:pos_class]:
        class_type = "S" + class_type
    if "abstract" in words[:pos_class]:
        class_type = "A" + class_type
    detail_class_mame = words[pos_class+1].split("<")[0]
    class_name = class_type + ":" + detail_class_mame
    detail_class_mame = concat(parentnode,detail_class_mame)
    des_node = fnod(class_name)
    del words[:pos_class+2]
    if words and istp(words[0]):
        tp_node = fnod("typeparams")
        type_params = handle_def(words[0][1:-1])
        type_params = [word for word in type_params if not istp(word)]
        while "extends" in type_params:
            pos = type_params.index("extends")
            tp_node.append(nod(type_params[pos-1]))
            del type_params[pos-1:pos+2]
        for tp in type_params:
            tp_node.append(nod(tp))
        des_node.append(tp_node)
        del words[0]
    if words and "extends" == words[0]:
        ex_node = fnod("extends")
        if len(words) > 2 and istp(words[2]):
            ex_node.append(nod(words[1]+words[2]))
            del words[:3]
        else:
            ex_node.append(nod(words[1]))
            del words[:2]
        des_node.append(ex_node)
    if words and "implements" == words[0]:
        impl_node = fnod("implements")
        del words[0]
        t = 0
        while t < len(words):
            if t != len(words)-1 and istp(words[t+1]):
                impl_node.append(nod(words[t]+words[t+1]))
                t+=2
            else:
                impl_node.append(nod(words[t]))
                t+=1
        des_node.append(impl_node)
    if field_node is not None:
        des_node.append(field_node)
    return des_node,detail_class_mame

# 对一个类进行处理
def handle_class(description,body,parentnode = None):
    description = " ".join([word for word in description.split(" ") if not word.startswith("@")])
    class_node,this_class_name = handle_class_des(description,parentnode)
    params_node = fnod("params")
    has_params = False
    inner_class_node = fnod("inner class")
    has_inner_class = False
    func_node = fnod("function")
    has_func = False
    segments = divise(body[1:-1])
    for index,segment in enumerate(segments):
        if segment.endswith("};"):
            has_params = True
            params_node.append(handle_param(segments[index-1]+segment))
        elif segment.endswith(";"):
            has_params = True
            params_node.append(handle_param(segment))
        elif segment.endswith(")"):
            has_func = True
            func_node.append(handle_func(segment))
        elif segment.endswith("throws E"):
            has_func = True
            func_node.append(handle_func(segment[:-9]))
        elif segment.endswith("}"):
            pass
        elif not segment.endswith("="):
            has_inner_class = True
            inner_class_node.append(handle_class(segment,segments[index+1],this_class_name))
    if has_params:
        class_node.append(params_node)
    if has_inner_class:
        class_node.append(inner_class_node)
    if has_func:
        class_node.append(func_node)
    return class_node

# 处理文件,生成一个类节点
def handle_file(file_path):
    try:
        result = prehandle(file_path)
        return handle_class(result[0],result[1])
    except Exception:
        print(f"在处理文件{file_path}时发生异常")
        sys.exit(1)

# 递归处理文件夹
def handle_dir(dir_path):
    dir_name = str(dir_path).split("\\")[-1]
    dir_node = fnod(dir_name)
    dir_node.append(Element("icon",{"BUILTIN":"folder"}))
    for subpath in dir_path.iterdir():
        if subpath.is_file():
            dir_node.append(handle_file(subpath))
        else:
            dir_node.append(handle_dir(subpath))
    return dir_node

def main():
    pathname = sys.argv[1]
    if len(sys.argv) == 3:
        name = sys.argv[2]
    else:
        name = pathname
    pathobj = Path(pathname)
    if pathobj.is_dir():
        thisnode = handle_dir(pathobj)
    else:
        thisnode = handle_file(pathobj)
    root_node = Element("map", {"version": "1.0.1"})
    root_node.append(thisnode)
    tree = ET.ElementTree(root_node)
    ET.indent(tree, space="  ", level=0)
    tree.write(f"{name}.mm", encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    main()