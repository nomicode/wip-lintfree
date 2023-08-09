import os
import pathlib
import re
from operator import itemgetter

import natsort

from . import format
from .. import errors
from .handlers.jq import JQHandler
from .handlers.regex import RegexHandler
from .handlers.xpath import XPathHandler


class Parser:

    _app = None
    _debug = None
    _config = None

    _input = None

    _config = None

    _handler_classes = {
        "regex": RegexHandler,
        "xpath": XPathHandler,
        "jq": JQHandler,
    }

    # TODO: Move this to an in-built parser config
    _command_regex = (
        r"::(\w+) "
        + r"(file=([^,]+))?(,line=(\d+))?(,endLine=(\d+))?(,title=(.+))?"
        + r"::(.*)"
    )

    _regex_matchers = []
    _annotations = []

    _name = None

    _severities = ["notice", "warning", "error"]

    _highest_severity = 0

    _error_severity = 0

    def __init__(self, app, config):
        self._app = app
        self._config = config

    def _read_config(self, format):
        # TODO: Catch errors
        self._name = self._config["name"]

        formats = self._config.get("formats")
        try:
            self._config = formats[format]
        except KeyError as err:
            formats = ", ".join(formats.keys())
            message = (
                f"Format not defined in parser configuration: {format}\n\n"
                + f"Available formats: {formats}"
            )
            raise errors.NoFormatError(message=message) from err

        # self._severities = self._format.get("severities")

        # for severity, severity in enumerate(self._severity_levels):
        #     severity = self._severities.get(severity)
        #     if severity:
        #         severity["severity_name"] = severity
        #         severity["severity_level"] = severity

    # TODO: Introduce annotation classes to handle this
    def _make_annotations(self, debug):
        syntax = self._config.get("syntax")
        try:
            handler_class = self._handler_classes[syntax]
        except KeyError as err:
            syntaxes = ", ".join(self._handler_classes.keys())
            message = (
                f"Unknown syntax: {syntax}\n\nSupported syntaxes: {syntaxes}"
            )
            raise errors.NoFormatError(message=message) from err
        if handler_class:
            handler = handler_class(self._severities, self._config)
            return handler.annotate(self._input, debug)
        return []

    def parse(self, input, format, debug):
        # TODO: Figure out a better way to check for this
        if not self._app._quiet and input.name == "<stdin>":
            # Figure out how to do this with the logging plugin for Click
            print("Reading from standard input...")
        self._input = input.read()
        self._read_config(format)
        self._annotations = self._make_annotations(debug)

    def _dedupe_annotations(self):
        unique_annotations = []
        for annotation in self._annotations:
            if annotation not in unique_annotations:
                unique_annotations.append(annotation)
        self._annotations = unique_annotations

    def _add_severity_level(self, annotation):
        severity = annotation["severity"]
        # TODO: Catch errors if severity isn't valid
        severity_level = self._severities.index(severity) + 1
        annotation["severity_level"] = severity_level
        if severity_level > self._highest_severity:
            self._highest_severity = severity_level

    def _add_location(self, annotation):
        file = pathlib.Path(annotation["filename"])
        annotation["filename"] = file.relative_to(".")
        if annotation["end_line"] is None:
            annotation["end_line"] = annotation["line"]
        filename = annotation["filename"]
        line = annotation["line"]
        end_line = annotation["end_line"]
        annotation["location"] = f"{filename}:{line}:{end_line}"

    def _process_options(self, annotation):
        if not self._config:
            return
        options = self._config.get("options")
        if not options:
            return
        if options.get("capitalize"):
            annotation["message"] = annotation["message"].capitalize()

    def _normalize_annotations(self):
        for annotation in self._annotations:
            self._add_severity_level(annotation)
            self._add_location(annotation)
            self._process_options(annotation)

    def _sort_annotations(self, sort_by):
        if sort_by == "filename":
            self._annotations = natsort.os_sorted(
                self._annotations, key=itemgetter("location")
            )
        if sort_by == "severity":
            self._annotations = natsort.os_sorted(
                self._annotations,
                key=itemgetter("severity_level"),
                reverse=True,
            )

    def _postprocess_annotations(self, sort_by):
        self._dedupe_annotations()
        self._normalize_annotations()
        self._sort_annotations(sort_by)

    def _get_status_code(self, error_on):
        try:
            error_on_severity = self._severities.index(error_on) + 1
        except ValueError as err:
            raise errors.ConfigurationError(
                message=f"Invalid severity name: {error_on}"
            ) from err
        return (
            100 + self._highest_severity
            if self._highest_severity >= error_on_severity
            else 0
        )

    def read_commands(self, read_file):
        command_regex_re = re.compile(self._command_regex)
        content = read_file.read()
        for line in content.splitlines():
            matches = command_regex_re.match(line)
            if not matches:
                continue
            groups = matches.groups()
            annotation = {
                "severity": groups[0],
                "filename": groups[2],
                "line": groups[4],
                "end_line": groups[6],
                "title": groups[8],
                "message": groups[9],
            }
            self._annotations.append(annotation)

    def _add_console_class(self, formatter_classes):
        if self._app._console:
            formatter_classes.append(format.ConsoleFormater)

    def _writing_to_file(self, write_file):
        return write_file is not None and write_file.name != "/dev/stdout"

    def _github_actions(self):
        return os.environ.get("GITHUB_ACTIONS") == "true"

    # TODO: Make output of GitHub commands configurable with a CLI option
    def _add_command_class(self, formatter_classes, write_file):
        if self._writing_to_file(write_file) or self._github_actions():
            formatter_classes.append(format.CommandFormater)

    def _get_formatter_classes(self, write_file):
        formatter_classes = []
        self._add_console_class(formatter_classes)
        self._add_command_class(formatter_classes, write_file)
        return formatter_classes

    def _format(self, write_file, before_context, after_context):
        for formatter_class in self._get_formatter_classes(write_file):
            formatter = formatter_class(
                self._name, self._annotations, before_context, after_context
            )
            formatter.run(write_file)

    def print(
        self, error_on, write_file, sort_by, before_context, after_context
    ):
        self._postprocess_annotations(sort_by)
        self._format(write_file, before_context, after_context)
        return self._get_status_code(error_on)
