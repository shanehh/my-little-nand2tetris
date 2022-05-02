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


# vm segement to assemble pre-defined register
registers = {
    # virtual segments
    "local": "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT",
    #
    "pointer": 3,
    "temp": 5,
    "static": 16,
}

# vm commands to assemble operator
operator_symbols = {
    "add": "+",
    "sub": "-",
    "and": "&",
    "or": "|",
    "neg": "-",
    "not": "!",
    "eq": "JEQ",
    "lt": "JLT",
    "gt": "JGT",
}


class Label:
    """generate label with index to avoid name conflicts
    {name}.{index}
    """

    count = defaultdict(int)

    def __init__(self, name) -> None:
        label = f"{name}.{self.count[name]}".upper()
        self.count[name] += 1

        self.address = "@{}".format(label)
        self.define = "({})".format(label)


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
        for line in self.read_code():
            tokens = line.split()
            yield tokens


class Translator:
    def init(self):
        yield from self.load_const(256, "SP")

    def load_const(self, const: int, to: str):
        """load a const to an arbitrary register

        Args:
            const (int): a number
            to (str, optional): the name of register. Defaults to "D".
        """
        yield "@{}".format(const)
        yield "D=A"
        if to != "D":
            yield "@{}".format(to)
            yield "M=D"

    def stack_push(self, what: str):
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

    def stack_pop(self, what: str):
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

    def push_pop(self, action: str, segment: str, index: int):
        match segment:
            case "constant":
                assert action != "pop"
                yield from self.load_const(index, "D")
                yield from self.stack_push("D")

            case "temp":
                assert 0 <= index <= 7

                address = "@{}".format(registers[segment] + index)
                match action:
                    case "push":
                        yield address
                        yield "D=M"
                        yield from self.stack_push("D")
                    case "pop":
                        yield from self.stack_pop("D")
                        yield address
                        yield "M=D"

            case "local" | "argument" | "this" | "that":
                if action == "pop":
                    # pop to D
                    # and save it to R13
                    yield from self.stack_pop("D")
                    yield "@R13"
                    yield "M=D"

                    yield from self.load_const(index, "D")

                    # save address (M[pointer] + index) to R14
                    yield "@{}".format(registers[segment])
                    yield "D=D+M"
                    yield "@R14"
                    yield "M=D"

                    # M[M[R14]] = M[R13]
                    yield "@R13"
                    yield "D=M"

                    yield "@R14"
                    yield "A=M"
                    yield "M=D"
                elif action == "push":
                    yield from self.load_const(index, "D")
                    yield "@{}".format(registers[segment])
                    yield "A=D+M"
                    yield "D=M"
                    yield from self.stack_push("D")

    def arithmetic(self, operator: str):
        match operator:
            case "add" | "sub" | "and" | "or":
                yield from self.stack_pop("D")
                yield from self.stack_pop("D=M{}D".format(operator_symbols[operator]))
                yield from self.stack_push("D")

            case "neg" | "not":
                yield from self.stack_pop("D")
                yield "D={}D".format(operator_symbols[operator])
                yield from self.stack_push("D")

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

                yield from self.stack_pop("D")
                # have to M-D
                # because x is under the y, or x is pushed first
                yield from self.stack_pop("D=M-D")
                set_true = Label("set_true")

                yield set_true.address
                yield "D;{}".format(operator_symbols[operator])

                endjump = Label("endjump")
                # default: set_false
                yield from self.stack_push("0")
                yield endjump.address
                yield "0;JMP"

                yield set_true.define
                yield from self.stack_push("-1")

                yield endjump.define

    def translate(self, tokens: list[str]):
        match tokens:
            case ["push" | "pop" as action, segment, index]:
                yield from self.push_pop(action, segment, int(index))
            case [operator]:
                yield from self.arithmetic(operator)
            case _:
                raise Exception(f"WTF is {tokens}")


if __name__ == "__main__":
    import sys

    vm_file = Path(sys.argv[1])
    asm_file = vm_file.with_suffix(".asm")
    translator = Translator()
    with open(asm_file, "wt+") as out:
        for code in translator.init():
            out.write(code + "\n")
        
        for tokens in Parser(vm_file).commands():
            for code in translator.translate(tokens):
                out.write(code + "\n")
