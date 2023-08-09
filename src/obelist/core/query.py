import json
import re

import charset_normalizer
import pyjq
from lxml import etree

from .. import errors


class Handler:

    _format = {}

    _match_attrs = {}

    _severities = []

    def __init__(self, format):
        self._format = format
        severities = self._format["severities"]
        self._match_attrs = self._format["match-attrs"]
        for severity_name in severities:
            severity = severities.get(severity_name)
            self._severities.append(severity)

    def _decode(self, bytes):
        # TODO: Catch encoding errors
        charset_data = charset_normalizer.from_bytes(bytes).best()
        return str(charset_data)

    def _handle_match(self, severity, match_attrs, match, attr_fn):
        # TODO: Catch errors
        file = match_attrs["file"]
        line = match_attrs["line"]
        end_line = match_attrs["end_line"]
        title = match_attrs["title"]
        message = match_attrs["message"]
        annotation = {
            "severity_name": severity["severity_name"],
            "file": attr_fn(match, file),
        }
        annotation["line"] = attr_fn(match, line)
        annotation["end-line"] = attr_fn(match, end_line)
        annotation["title"] = attr_fn(match, title)
        annotation["message"] = attr_fn(match, message)
        return annotation

    def _handle_severity(self, severity, matches_fn, attr_fn):
        matches = matches_fn(severity["match"])
        match_attrs = severity.get("match-attrs", self._match_attrs)
        if not match_attrs.get("end_line"):
            match_attrs["end_line"] = match_attrs["line"]
        for match in matches:
            yield self._handle_match(severity, match_attrs, match, attr_fn)

    def _query_annotations(self, matches_fn, attr_fn):
        annotations = []
        for severity in self._severities:
            annotations.extend(
                self._handle_severity(severity, matches_fn, attr_fn)
            )
        return annotations

    def annotate(self, input):
        raise errors.NotImplementedError


class RegexHandler(Handler):
    def __init__(self, format):
        super().__init__(format)
        # Compile regular expressions (and catch any errors)
        for severities in self._severities:
            # TODO: Catch errors
            match = severities["match"]
            severities["match_re"] = re.compile(match)

    def _get_match(self, line):
        for severity in self._severities:
            return severity["match_re"].search(line)

    def _get_matches(self, input):
        matches = []
        input_lines = input.strip().splitlines()
        for line in input_lines:
            line = line.rstrip("\n")
            if match := self._get_match(line):
                matches.append(match)
        return matches

    def _add_file(self, match_attrs, match, annotation):
        file = match_attrs["file"]
        if match_groupdict := match.groupdict():
            file = file.format(**match_groupdict)
        if match_groups := match.groups():
            file = file.format(*match_groups)
        annotation["file"] = file
        return annotation

    def _add_line(self, match_attrs, match, annotation):
        line = match_attrs["line"]
        if match_groupdict := match.groupdict():
            line = line.format(**match_groupdict)
        if match_groups := match.groups():
            line = line.format(*match_groups)
        annotation["line"] = line
        return annotation

    def _add_end_line(self, match_attrs, match, line, annotation):
        end_line = match_attrs.get("end-line", line)
        if end_line == line:
            return annotation
        if match_groupdict := match.groupdict():
            end_line = line.format(**match_groupdict)
        if match_groups := match.groups():
            end_line = line.format(*match_groups)
        annotation["end-line"] = end_line
        return annotation

    def _add_title(self, match_attrs, match, annotation):
        title = match_attrs["title"]
        if match_groupdict := match.groupdict():
            title = title.format(**match_groupdict)
        if match_groups := match.groups():
            title = title.format(*match_groups)
        annotation["title"] = title
        return annotation

    def _add_message(self, match_attrs, match, annotation):
        message = match_attrs["message"]
        if match_groupdict := match.groupdict():
            message = message.format(**match_groupdict)
        if match_groups := match.groups():
            message = message.format(*match_groups)
        annotation["message"] = message
        return annotation

    def _create_annotation(self, matcher, match, line):
        annotation = {"severity_name": matcher["severity_name"]}
        match_attrs = matcher.get("match-attrs", self._match_attrs)
        annotation = self._add_file(match_attrs, match, annotation)
        annotation = self._add_line(match_attrs, match, annotation)
        annotation = self._add_end_line(match_attrs, match, line, annotation)
        annotation = self._add_title(match_attrs, match, annotation)
        annotation = self._add_message(match_attrs, match, annotation)

    def _get_annotations(self, matches):
        annotations = []
        # TODO: Handle exceptions when a user tries to use positional and named
        # groups simultaneously
        for line, matcher, match in matches:
            annotation = self._create_annotation(matcher, match, line)
            annotations.append(annotation)
        return annotations

    def annotate(self, input):
        input = self._decode(input)
        matches = self._get_matches(input)
        return self._get_annotations(matches)


class XPathHandler(Handler):
    def annotate(self, input):
        root = etree.fromstring(input)

        def matches_fn(query):
            return root.xpath(query)

        def attr_fn(match, attr):
            return match.xpath(attr)[0]

        return self._query_annotations(matches_fn, attr_fn)


class JQHandler(Handler):
    def annotate(self, input):
        input = self._decode(input)
        json_dict = json.loads(input)

        def matches_fn(query):
            return pyjq.all(query, json_dict)

        def attr_fn(match, attr):
            return pyjq.all(attr, match)[0]

        return self._query_annotations(matches_fn, attr_fn)
