"""Two-pass assembler for the Hack assembly language.

Student: Tanay Garg | Roll No.: 2501730136 | K = 36
For K % 3 == 0, labels and variables are also written to symbols.txt.
"""

from pathlib import Path
import sys


STUDENT_NAME = "Tanay Garg"
ROLL_NUMBER = "2501730136"
PERSONAL_K = 36

COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010", "D": "0001100", "A": "0110000",
    "!D": "0001101", "!A": "0110001", "-D": "0001111", "-A": "0110011",
    "D+1": "0011111", "A+1": "0110111", "D-1": "0001110", "A-1": "0110010",
    "D+A": "0000010", "D-A": "0010011", "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    "M": "1110000", "!M": "1110001", "-M": "1110011", "M+1": "1110111", "M-1": "1110010",
    "D+M": "1000010", "D-M": "1010011", "M-D": "1000111", "D&M": "1000000", "D|M": "1010101",
}
DEST = {
    "": "000", "M": "001", "D": "010", "MD": "011",
    "A": "100", "AM": "101", "AD": "110", "AMD": "111",
}
JUMP = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

PREDEFINED_SYMBOLS = {
    **{f"R{i}": i for i in range(16)},
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "SCREEN": 16384,
    "KBD": 24576,
}


class AsmError(Exception):
    """An assembly-language syntax or encoding error."""


def clean(line):
    """Remove a line comment, spaces, and surrounding whitespace."""
    return line.split("//", 1)[0].replace(" ", "").strip()


def valid_symbol(symbol):
    if not symbol or symbol[0].isdigit():
        return False
    return all(char.isalnum() or char in "_.$:" for char in symbol)


def translate_c(line):
    if line.count("=") > 1 or line.count(";") > 1:
        raise AsmError("invalid instruction")

    dest, rest = line.split("=", 1) if "=" in line else ("", line)
    comp, jump = rest.split(";", 1) if ";" in rest else (rest, "")

    if comp not in COMP:
        raise AsmError(f"invalid instruction (unknown comp '{comp}')")
    if dest not in DEST:
        raise AsmError(f"invalid instruction (unknown dest '{dest}')")
    if jump not in JUMP:
        raise AsmError(f"invalid instruction (unknown jump '{jump}')")

    return "111" + COMP[comp] + DEST[dest] + JUMP[jump]


def assemble(path):
    """Assemble path and return machine words, errors, and exported symbols."""
    path = Path(path)
    symbols = dict(PREDEFINED_SYMBOLS)
    labels = {}
    variables = {}
    errors = []

    try:
        with path.open("r", encoding="utf-8") as source:
            lines = [(number, clean(line)) for number, line in enumerate(source, start=1)]
    except OSError as error:
        return [], [f"Could not read '{path}': {error}"], {}

    lines = [(number, line) for number, line in lines if line]

    # Pass 1: record labels at their ROM addresses.
    code = []
    rom_address = 0
    for number, line in lines:
        if line.startswith("("):
            name = line[1:-1] if line.endswith(")") else ""
            if not line.endswith(")") or not valid_symbol(name):
                errors.append(f"Line {number}: invalid label '{line}'")
            elif name in labels or name in PREDEFINED_SYMBOLS:
                errors.append(f"Line {number}: duplicate or reserved label '{name}'")
            else:
                labels[name] = rom_address
                symbols[name] = rom_address
        else:
            code.append((number, line))
            rom_address += 1

    # Pass 2: encode instructions and allocate RAM addresses to new variables.
    output = []
    next_variable = 16
    for number, line in code:
        try:
            if line.startswith("@"):
                symbol = line[1:]
                if symbol.isdigit():
                    value = int(symbol)
                    if value > 32767:
                        raise AsmError(f"invalid instruction (value {value} too large)")
                elif valid_symbol(symbol):
                    if symbol not in symbols:
                        if next_variable > 16383:
                            raise AsmError("no available RAM addresses for another variable")
                        symbols[symbol] = next_variable
                        variables[symbol] = next_variable
                        next_variable += 1
                    value = symbols[symbol]
                else:
                    raise AsmError(f"invalid instruction (bad symbol '{symbol}')")
                output.append("0" + format(value, "015b"))
            else:
                output.append(translate_c(line))
        except AsmError as error:
            errors.append(f"Line {number}: {error}")

    exported_symbols = {
        **{name: (address, "label") for name, address in labels.items()},
        **{name: (address, "variable") for name, address in variables.items()},
    }
    return output, errors, exported_symbols


def write_symbols(path, exported_symbols):
    """Write the K-dependent label/variable address table."""
    path = Path(path).with_name("symbols.txt")
    lines = [
        f"# Student: {STUDENT_NAME} | Roll No.: {ROLL_NUMBER} | K = {PERSONAL_K}",
        "# Symbol Address Type",
    ]
    for name, (address, kind) in sorted(
        exported_symbols.items(), key=lambda item: (item[1][0], item[0])
    ):
        lines.append(f"{name} {address} {kind}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Usage: python assembler.py <file.asm>")
        return 2

    source_path = Path(argv[0])
    output, errors, exported_symbols = assemble(source_path)
    if errors:
        for error in errors:
            print(error)
        print(f"{len(errors)} error(s). No .hack file written.")
        return 1

    output_path = source_path.with_suffix(".hack")
    output_path.write_text("\n".join(output) + "\n", encoding="ascii")
    print("Wrote", output_path)

    if PERSONAL_K % 3 == 0:
        symbols_path = write_symbols(source_path, exported_symbols)
        print("Wrote", symbols_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
