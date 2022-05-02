"""
reference

see 7.4.1    Standard VM Mapping on the Hack Platform, Part I
"""

from functools import wraps
from pathlib import Path
from typing import Iterable, Callable
from os import PathLike
from enum import Enum
from collections import defaultdict

count = defaultdict(int)
def label(name :str) -> str:
    """generate label with index to avoid name conflicts

    Args:
        name (str): the name of the label

    Returns:
        str: {name}.{index}
    """
    count[name] += 1
    return f"{name}.{count[name]}"

#     # "constant": 
# {
#     "local": 1,
#     "argument": 2,
#     "this": 3,
#     "that": 4,
#     "temp": 5
# }

# push constant 7
# ->
# RAM[SP] = 7
# SP += 1
SP = 256


class Stack:
    """
    SP is a pointer
    """
    
    @staticmethod
    def push(what: str):
        """
        set the value of the tip of stack
        and move forward
        """
        # M[M[SP]] = D  // ok, we know SP == 0
        yield "@SP"
        yield "A=M"
        yield f"M={what}"

        # SP = SP + 1
        yield "@SP"
        yield "M=M+1"

    @staticmethod
    def pop(what: str):
        """
        move back stack pointer
        and ready to get the value of the tip of stack, by M
        """
        # SP = SP - 1
        yield "@SP"
        yield "M=M-1"

        yield "@SP"
        yield "A=M"
        if "=" in what:
            yield what
        else:
            yield f"{what}=M"



class Parser:
    def __init__(self, filepath: PathLike):
        self.filepath = filepath

    def skip(self, code: Iterable[str], predicate: Callable[[str], bool]):
        for line in code:
            if predicate(line):
                continue
            else:
                yield line

    def tidy(self, code: Iterable[str]):
        """
        strip and skip comment, empty line
        """
        code = map(lambda line: line.split("//")[0], code)
        code = map(str.strip, code)
        # skip empty
        code = self.skip(code, lambda line: len(line) == 0)
        return code


    def read_code(self):
        with open(self.filepath, "rt") as code:
            yield from self.tidy(code)

    def commands(self):
        # init
        yield "@256"
        yield "D=A"
        yield "@SP"
        yield "M=D"

        
        for line in self.read_code():
            tokens = line.split()
            match tokens:
                case ["push", segment, index]:
                    assert segment == "constant"
                    yield f"@{index}"
                    yield "D=A"
                    yield from Stack.push("D")
                case [operator]:
                    match operator:
                        case "add" | "sub" | "and" | "or":
                            yield from Stack.pop("D")
                            match operator:
                                case "add":
                                    yield from Stack.pop("D=M+D")
                                case "sub":
                                    yield from Stack.pop("D=M-D")
                                case "and":
                                    yield from Stack.pop("D=M&D")
                                case "or":
                                    yield from Stack.pop("D=M|D")

                            yield from Stack.push("D")

                        case "neg" | "not":
                            yield from Stack.pop("D")
                            match operator:
                                case "neg":
                                    yield "D=-D"
                                case "not":
                                    yield "D=!D"
                            yield from Stack.push("D")

                        case "eq" | "lt" | "gt":
                            """
                            algorithm:
                            
                            if true
                                goto set_true
                            (set_false)
                                push 0
                                goto endjump
                            (set_true)
                                push -1
                            (endjump)
                            """
                            
                            yield from Stack.pop("D")
                            # have to M-D
                            # because x is under the y, or x is pushed first
                            yield from Stack.pop("D=M-D")
                            set_true =label("set_true")

                            yield f"@{set_true}"
                            match operator:
                                case "eq":
                                    yield "D;JEQ"
                                case "lt":
                                    yield "D;JLT"
                                case "gt":
                                    yield "D;JGT"

                            endjump =label("endjump")
                            # default: set_false
                            yield from Stack.push("0")
                            yield f"@{endjump}"
                            yield "0;JMP"
                            
                            yield f"({set_true})"
                            yield from Stack.push("-1")

                            yield f"({endjump})"
                
                case _:
                    raise Exception(f"WTF is {tokens}")




if __name__ == "__main__":
    import sys

    vm_file = Path(sys.argv[1])
    asm_file = vm_file.with_suffix(".asm")
    with open(asm_file, "wt+") as out:
        for command in Parser(vm_file).commands():
            out.write(command + "\n")