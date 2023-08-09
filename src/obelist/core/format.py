import os
import shutil
import textwrap

import charset_normalizer
import pastel

printer = pastel.Pastel(True)
printer.add_style("header", options=["bold"])
printer.add_style("location", "light_blue")
printer.add_style("context", options=["italic"])
printer.add_style("highlight", options=["italic", "bold"])
printer.add_style("notice", options=["bold"])
printer.add_style("warning", "yellow", options=["bold"])
printer.add_style("error", "red", options=["bold"])

# For debug output
printer.add_style("set", "yellow")
printer.add_style("add", "green")


class BaseFormater:

    _github = False

    _name = None
    _annotations = []

    _write_file = None

    _terminal_width = None
    _before_context = None
    _after_context = None

    def __init__(self, name, annotations, before_context, after_context):
        self._name = name
        self._annotations = annotations
        self._terminal_width = shutil.get_terminal_size().columns
        self._before_context = before_context
        self._after_context = after_context

    def _get_title(self, annotation):
        title = annotation.get("title")
        if title:
            return title
        title = self._name
        if code := annotation.get("code"):
            title = f"{self._name}: {code}"
        return title

    def _print(self, str):
        print(printer.colorize(str))

    def _print_prologue(self):
        pass

    def _print_annotation(self, annotation):
        pass

    def _print_annotations(self):
        for annotation in self._annotations:
            self._print_annotation(annotation)

    def _print_epilogue(self):
        pass

    def run(self, write_file):
        self._write_file = write_file
        if self._annotations:
            self._print_prologue()
            self._print_annotations()
            self._print_epilogue()


class CommandFormater(BaseFormater):
    def _handle_command(self, output):
        if (
            self._write_file.name == "/dev/stdout"
            and os.environ.get("GITHUB_ACTIONS") == "true"
        ):
            # TODO: Not sure why, but we need to print here to get this working
            # on GitHub Actions
            print(output)
        else:
            self._write_file.write(output + "\n")

    def _print_prologue(self):
        # TODO: Inflect this name from somewhere
        name = self._name or "Obelist"
        group = f"::group::{name}"
        self._handle_command(group)

    def _print_annotation(self, annotation):
        severity = annotation["severity"]
        file = f"file={annotation['filename']}"
        line = f",line={int(annotation['line'])}"
        end_line = ""
        if annotation["line"] != annotation["end_line"]:
            end_line = f",endLine={int(annotation['end_line'])}"
        title = f",title={self._get_title(annotation)}"
        message = annotation["message"].strip()
        self._handle_command(
            f"::{severity} {file}{line}{end_line}{title}::{message}"
        )

    def _print_epilogue(self):
        self._handle_command("::endgroup::")


class ConsoleFormater(BaseFormater):

    _first_location = True
    _previous_location = None

    def _wrap_line(self, line):
        yield from textwrap.wrap(line, self._terminal_width)

    def _wrap_lines(self, lines):
        for line in lines:
            if line:
                yield from self._wrap_line(line)
                continue
            yield ""

    def _pad_output(self, lines):
        for line in self._wrap_lines(lines):
            line_len = len(line) + 2
            if line_len < self._terminal_width:
                line = line + " " * (self._terminal_width - line_len)
            yield line

    def _get_before_context(self, lines, line):
        before_lines = lines[line - self._before_context : line]
        before_lines = self._pad_output(before_lines)
        return "\n".join(before_lines)

    def _get_after_context(self, lines, end_line):
        after_lines = lines[end_line + 1 : end_line + self._after_context]
        after_lines = self._pad_output(after_lines)
        return "\n".join(after_lines)

    def _get_highlight(self, lines, line, end_line):
        if line == end_line:
            highlight_lines = [lines[line]]
        else:
            highlight_lines = lines[line : end_line + 1]
        highlight_lines = self._pad_output(highlight_lines)
        return "\n".join(highlight_lines)

    def _quote(self, lines):
        if lines.strip():
            quoted_lines = [f"> {line}" for line in lines.splitlines()]
            lines = "\n".join(quoted_lines)
        return lines

    def _print_line(self, lines, line, highlight):
        before_context = self._get_before_context(lines, line)
        after_context = self._get_after_context(lines, line)
        if before_context.strip():
            self._print(f"<context>{self._quote(before_context)}</context>")
        self._print(f"<highlight>{self._quote(highlight)}</highlight>")
        if after_context.strip():
            self._print(f"<context>{self._quote(after_context)}</context>")

    # TODO: DRY out this method (used elsewhere)
    def _decode(self, bytes):
        # TODO: Catch encoding errors
        charset_data = charset_normalizer.from_bytes(bytes).best()
        return str(charset_data)

    def _print_lines(self, filename, line, end_line):
        line -= 1
        end_line -= 1
        with open(filename, "rb") as file:
            bytes = file.read()
            lines = self._decode(bytes).splitlines()
            # Add an extra empty line to account for the final empty newline
            lines.append("")
            if line - 1 > len(lines):
                return
            highlight = self._get_highlight(lines, line, end_line)
            if highlight.strip():
                self._print_line(lines, line, highlight)

    def _print_annotation(self, annotation):
        filename = annotation["filename"]
        line = int(annotation["line"])
        end_line = int(annotation["end_line"])
        end_line_str = "" if end_line == line else f":{end_line}"
        location = f"<location>{filename}:{line}{end_line_str}</location>"
        if not self._first_location:
            self._first_location = False
            print("")
        if location != self._previous_location:
            self._first_location = False
            self._print(location)
            self._print_lines(filename, line, end_line)
        severity = annotation["severity"]
        # TODO: Make it optional to append `severity` to the title for console
        # output
        # severity_str = annotation["severity"].capitalize()
        title = self._get_title(annotation)
        title = f"<{severity}>{title}</{severity}>"
        msg = annotation["message"].strip()
        indent = "    "
        msg = textwrap.fill(
            msg,
            self._terminal_width,
            initial_indent=indent,
            subsequent_indent=indent,
        )
        msg = msg.lstrip()
        self._print(f"  {title}\n{indent}{msg}")
