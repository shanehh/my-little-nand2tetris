from functools import wraps
from pathlib import Path


class SymbolTable(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for i in range(16):
            self[f"R{i}"] = i

        self["SP"] = 0
        self["LCL"] = 1
        self["ARG"] = 2
        self["THIS"] = 3
        self["THAT"] = 4
        self["SCREEN"] = 16384
        self["KBD"] = 24576

        self._symbol_count = 16

    def add(self, symbol: str):
        if symbol in self:
            return
        else:
            self[symbol] = self._symbol_count
            self._symbol_count += 1


# <symbol: str, address: int>
symbol_table = SymbolTable()


class Instruction:
    A = "A"
    C = "C"

    def __init__(self, instruction: str):
        self.ins = instruction

        if instruction.startswith("@"):
            self.type = self.A
        else:
            # dest = comp ; jump
            self.type = self.C

    @staticmethod
    def instruction_property(type_):
        """
        specify which type instruction have the property
        """

        def property_decorator(method):
            @wraps(method)
            def wrapper(self):
                if self.type != type_:
                    raise Exception(f"Not {type_}-instruction")
                else:
                    return method(self)

            return property(wrapper)

        return property_decorator

    c_property = instruction_property(C)
    a_property = instruction_property(A)

    @staticmethod
    def canonical(s: str):
        # " jgt" -> "JGT"
        return s.strip().upper()

    @c_property
    def dest(self):
        if "=" in self.ins:
            return self.canonical(self.ins.split("=")[0])
        else:
            return None

    @c_property
    def comp(self):
        """
        comp is mandatory.
        If dest is empty, the = is omitted
        If jump is empty, the ; is omitted
        """
        cmp = self.ins

        if self.dest is not None:
            cmp = cmp.split("=")[1]

        if self.jump is not None:
            cmp = cmp.split(";")[0]

        return self.canonical(cmp)

    @c_property
    def jump(self):
        if ";" in self.ins:
            return self.canonical(self.ins.split(";")[1])
        else:
            return None

    @a_property
    def value(self) -> str:
        # '@2' -> '2'
        return self.ins[1:]

    @a_property
    def is_symbol(self):
        return not self.value.isdigit()

    def __repr__(self) -> str:
        return self.ins


class Code:
    @staticmethod
    def dest(part: str):
        if part is None:
            return "000"
        else:
            code = lambda char: "1" if char in part else "0"
            return code("A") + code("D") + code("M")

    jump_table = {
        "JGT": "001",
        "JEQ": "010",
        "JGE": "011",
        "JLT": "100",
        "JNE": "101",
        "JLE": "110",
        "JMP": "111",
    }

    @classmethod
    def jump(self, part: str):
        if part is None:
            return "000"
        else:
            return self.jump_table[part]

    # see implementation of ALU
    # if these bits seems nonsensical
    comp_table = {
        "0": "101010",
        "1": "111111",
        "-1": "111010",
        "D": "001100",
        "R": "110000",
        "!D": "001101",
        "!R": "110011",
        "D+1": "011111",
        "R+1": "110111",
        "D-1": "001110",
        "R-1": "110010",
        "D+R": "000010",
        "D-R": "010011",
        "R-D": "000111",
        "D&R": "000000",
        "D|R": "010101",
    }

    @classmethod
    def comp(self, part: str):
        if "A" in part:
            a = "0"
            part = part.replace("A", "R")
        elif "M" in part:
            a = "1"
            part = part.replace("M", "R")
        else:
            a = "0"

        return a + self.comp_table[part]


class Parser:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def skip(self, code, predicate):
        for line in code:
            if predicate(line):
                continue
            else:
                yield line

    def tidy(self, code):
        """
        strip and skip comment, empty line
        """
        code = map(lambda line: line.split("//")[0], code)
        code = map(str.strip, code)
        return self.skip(code, lambda line: len(line) == 0)

    def first_pass(self, code):
        address = 0

        for line in code:
            # is Label declaration?
            if line.startswith("("):
                # "( foo bar) )" -> "foo bar"
                label = line.strip(" ()")
                symbol_table[label] = address
            else:
                if (ins := Instruction(line)).type == "A" and ins.is_symbol:
                    symbol = ins.value
                    symbol_table.add(symbol)

                address += 1

    def instructions(self):
        with open(self.filepath, "rt") as code:
            self.first_pass(self.tidy(code))

            code.seek(0)
            code = self.tidy(code)

            for line in self.skip(code, lambda line: line.startswith("(")):
                yield Instruction(line)


if __name__ == "__main__":
    import sys

    asm_file = Path(sys.argv[1])
    hack_file = asm_file.with_suffix(".hack")

    with open(hack_file, "wt+") as out:
        for ins in Parser(asm_file).instructions():
            print(ins)
            if ins.type == ins.A:
                if ins.is_symbol:
                    val = symbol_table[ins.value]
                else:
                    val = int(ins.value)
                code = "0" + "{0:015b}".format(val)
            else:
                code = (
                    "111"
                    + Code.comp(ins.comp)
                    + Code.dest(ins.dest)
                    + Code.jump(ins.jump)
                )
            out.write(code + "\n")
