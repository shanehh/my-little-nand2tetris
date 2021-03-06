"""
reference

see 7.4.1 Standard VM Mapping on the Hack Platform, Part I
see 8.6 Project

This version of the VM translator assumes that the source VM code is
error-free. Error checking, reporting, and handling can be added to later
versions of the VM translator but are not part of project 8.
"""

from collections import defaultdict
from enum import Enum
from functools import cached_property, wraps
from os import PathLike
from pathlib import Path
from typing import Callable, Iterable

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


class IncrementTable:
    def __init__(self):
        # index and filename
        self.store = {}
        self.count = 0

    def get(self, index: str) -> int:
        if index in self.store:
            return self.store[index]
        else:
            self.store[index] = self.count
            self.count += 1
            return self.store[index]


increment_table = IncrementTable()


class Label:
    """generate label with index to avoid name conflicts
    {name}.{index}
    """

    count = defaultdict(int)

    def __init__(self, name: str) -> None:
        label = f"{name}.{self.count[name]}".upper()
        self.count[name] += 1
        self.address = "@{}".format(label)
        self.define = "({})".format(label)

        self._name = name

    @cached_property
    def ret(self):
        return Label(f"{self._name}$ret")


class Parser:
    def __init__(self, path: PathLike):
        self.path = path

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

    def commands(self):
        """
        yield tokens and the filename
        """
        for vm_file in Path(self.path).glob("*.vm"):
            with open(vm_file, "rt") as code:
                for line in self.tidy(code):
                    tokens = line.split()
                    yield tokens, vm_file.stem


class Translator:
    def bootstrap(self):
        """
        One of the OS libraries, called Sys.vm, includes a method called init.
        The Sys.init function starts with some OS initialization code (we???ll deal with this
        later, when we discuss the OS), then it does call Main.main
        """
        yield from self.load_const(256, "SP")
        # Setting the LCL, ARG, THIS and THAT point??ers to known illegal values
        # helps identify when a pointer is used before it is initial??ized.
        yield from self.load_const(-1, "LCL")
        yield from self.load_const(-2, "ARG")
        yield from self.load_const(-3, "THIS")
        yield from self.load_const(-4, "THAT")

        # call Sys.init
        # ????????????????????????
        # # yield from self.translate(["goto", "Sys.init"])
        # ?????????????????? frame ?????? save ??? stack
        # ??????????????????????????????????????????????????????
        # ????????? `./ProgramFlow/FibonacciSeries/FibonacciSeries.tst`
        # ?????? `repeat 6000`????????????????????????????????? machine code ??????lol!
        yield from self.translate(["call", "Sys.init", "0"])

    def load_const(self, const: int, to: str):
        """load a const to an arbitrary register

        Args:
            const (int): a number
            to (str, optional): the name of register.
        """
        if const < 0:
            yield "@{}".format(abs(const))
            yield "D=A"
            yield "D=-D"
        else:
            yield "@{}".format(const)
            yield "D=A"

        if to != "D":
            yield "@{}".format(to)
            yield "M=D"

    def address_pointer(self, register: str):
        """
        *register
        """
        yield f"@{register}"
        yield "A=M"

    def stack_push(self, what: str):
        """
        set the value of the tip of stack
        and move forward
        """
        # M[M[SP]] = D  // ok, we know SP == 0
        yield from self.address_pointer("SP")
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

        yield from self.address_pointer("SP")
        if "=" in what:
            yield what
        else:
            yield f"{what}=M"

    def static_push_pop(self, action: str, index: int, filename: str):
        """
        // File Foo.vm
        pop static 5

        =>

        D = stack.pop (code omitted)
        @Foo.5
        M=D

        static variables should be seen by all the methods in a program

        solution:

        1. Have the VM translator translate each VM reference
        static i (in file Foo.vm) into an assembly reference Foo.i
        2. Following assembly, the Hack assembler will map these
        references onto RAM[16], RAM[17], ..., RAM[255]
        3. Therefore, the entries of the static segment will end up
        being mapped onto RAM[16], RAM[17], ..., RAM[255],
        in the order in which they appear in the program.
        """
        assert 0 <= index <= 255 - 16 + 1
        # figure out actual index
        index = registers["static"] + increment_table.get(f"{filename}.{index}")
        match action:
            case "pop":
                yield from self.stack_pop("D")
                yield "@{}".format(index)
                yield "M=D"
            case "push":
                yield "@{}".format(index)
                yield "D=M"
                yield from self.stack_push("D")

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

            case "pointer":
                assert 0 <= index <= 1
                # actual segment
                segment = "this" if index == 0 else "that"
                register = registers[segment]
                match action:
                    case "pop":
                        yield from self.stack_pop("D")
                        yield "@{}".format(register)
                        yield "M=D"
                    case "push":
                        yield "@{}".format(register)
                        yield "D=M"
                        yield from self.stack_push("D")

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

                    yield from self.address_pointer("R14")
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

    def label(self, name: str):
        """
        label declaration command
        """
        yield f"({name})"

    def goto(self, label_name: str):
        """
        // jump to execute the command just after label
        """
        yield f"@{label_name}"
        yield "0;JMP"

    def if_goto(self, label_name: str):
        """
        // cond = pop();
        // if cond jump to execute the command just after label
        """
        yield from self.stack_pop("D")
        yield f"@{label_name}"
        yield "D;JNE"

    def function(self, name: str, n_vars: int):
        """
        (f)                 // injects a function entry label into the code
        repeat nVars times: // nVars = number of local variables
            push 0          // initializes the local variables to 0
        """
        # function name
        yield f"({name})"
        for _ in range(n_vars):
            yield from self.stack_push("0")

    def ret(self):
        """
        endFrame = LCL              // endframe is a temporary variable
        retAddr = *(endFrame - 5)   // gets the return address
        *ARG = pop()                // repositions the return value for the caller
        SP = ARG + 1                // repositions SP of the caller
        THAT = *(endFrame - 1)      // restores THAT of the caller
        THIS = *(endFrame - 2)      // restores THIS of the caller
        ARG = *(endFrame - 3)       // restores ARG of the caller
        LCL = *(endFrame - 4)       // restores LCL of the caller
        goto retAddr                // goes to the caller's return address


        Functions with no arguments return to correct RIP (Return Instruction Point) with correct return value on stack.
        This can fail if the RIP is not correctly pushed on the stack by the calling code,
        or if the returning code does not store the RIP in a temporary register before overwriting it with the return value.

        ???????????? function
        RIP ??? return value ???????????????????????? bug ???????????????????????????
        """
        # endFrame(R13) = LCL // endframe is a temporary variable
        yield "@LCL"
        yield "D=M"
        yield "@R13"
        yield "M=D"

        def restore(register: str, offset: int):
            """
            restores registers of the caller
            e.g.
            THAT = ROM[endFrame ??? 1] // restores THAT of the caller
            """
            yield "@R13"  # endFrame
            yield "D=M"
            if offset == 1:
                yield "D=D-1"
            else:
                yield f"@{offset}"
                yield "D=D-A"
            yield "A=D"
            yield "D=M"
            yield f"@{register}"
            yield "M=D"

        # save return address to temporary register
        yield from restore("R14", 5)

        # let's *ARG = pop() // repositions the return value for the caller
        # also can write as:
        # # yield from self.translate(["pop","argument", "0"])
        #
        # ?????????????????? case?????? nArgs ??? 0 ???(Functions with no arguments)
        # ARG ??? return address/RIP(Return Instruction Point) ????????????????????????
        # # ARG = SP-5-nArgs // Repositions ARG
        # ???????????????
        # ??? return address ?????? temporary register?????? pop
        # ???????????????????????? layout ???????????????
        yield from self.stack_pop("D")
        yield from self.address_pointer("ARG")
        yield "M=D"

        # SP = ARG + 1 // repositions SP of the caller
        yield "@ARG"
        yield "D=M+1"
        yield "@SP"
        yield "M=D"

        # continue some restorings
        yield from restore("THAT", 1)
        yield from restore("THIS", 2)
        yield from restore("ARG", 3)
        yield from restore("LCL", 4)

        # finally, goodbye???I'm go home now
        # goto *R14(ROM[R14] is saved return address)
        yield from self.address_pointer("R14")
        yield "0;JMP"

    def call(self, function_name: str, n_args: int):
        """
        call Bar.mult 2

        will be translated to:

        // assembly code that saves the caller???s state on the stack,
        // sets up for the function call, and then:
            goto Bar.mult // (in assembly)
        (Foo$ret.1) // created and plugged by the translator
        """
        label = Label(function_name)

        # push retAddrLabel // Using a translator-generated label
        yield label.ret.address
        yield "D=A"
        yield from self.stack_push("D")

        # Saves registers of the caller
        for register in ["LCL", "ARG", "THIS", "THAT"]:
            yield f"@{register}"
            yield "D=M"
            yield from self.stack_push("D")

        # ARG = SP-5-nArgs // Repositions ARG
        yield "@SP"
        yield "D=M"
        yield "@5"
        yield "D=D-A"
        if n_args > 0:
            yield f"@{n_args}"
            yield "D=D-A"
        yield "@ARG"
        yield "M=D"

        # LCL = SP // Repositions LCL
        yield "@SP"
        yield "D=M"
        yield "@LCL"
        yield "M=D"

        # goto functionName // Transfers control to the called function
        yield from self.translate(["goto", function_name])

        # (retAddrLabel) // the same translator-generated label
        yield label.ret.define

    def translate(self, tokens: list[str], filename: str = None):
        match tokens:
            case ["return"]:
                yield from self.ret()
            case ["push" | "pop" as action, "static", index]:
                yield from self.static_push_pop(action, int(index), filename)
            case ["push" | "pop" as action, segment, index]:
                yield from self.push_pop(action, segment, int(index))
            case ["label", name]:
                yield from self.label(name)
            case ["goto", label]:
                yield from self.goto(label)
            case ["if-goto", label]:
                yield from self.if_goto(label)
            case [operator]:
                yield from self.arithmetic(operator)
            case ["function", name, n_vars]:
                yield from self.function(name, int(n_vars))
            case ["call", name, n_args]:
                yield from self.call(name, int(n_args))
            case _:
                raise Exception(f"WTF is {tokens}")


if __name__ == "__main__":
    import sys

    program_folder = Path(sys.argv[1])
    assert program_folder.is_dir()
    asm_file = program_folder / (program_folder.name + ".asm")
    translator = Translator()
    with open(asm_file, "wt+") as out:
        for code in translator.bootstrap():
            out.write(code + "\n")

        for tokens, filename in Parser(program_folder).commands():
            for code in translator.translate(tokens, filename):
                out.write(code + "\n")
