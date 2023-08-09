import re

from . import Handler


class RegexHandler(Handler):

    _rules = []
    _rewrites = []

    _current_annotation = None

    _required_attributes = ["filename", "line", "severity", "message"]

    def __init__(self, severities, config):
        super().__init__(severities, config)
        # Compile regular expressions (and catch any errors)
        for rule in self._rules:
            # TODO: Catch errors
            match = rule["match"]
            rule["match_re"] = re.compile(match)

    # TODO: Add color
    def _debug_groups(self, line, match):
        print(f"{line}\n")
        groups_len = len(match.groups())
        leading_zeros = len(str(groups_len))
        group_lines = []
        modifier = f":0{leading_zeros}d"
        for num, value in enumerate(match.groups()):
            fstring = 'f"    {' + f"{num}{modifier}" + "}: " + f'{value}"'
            groups_line = eval(fstring)
            group_lines.append(groups_line)
        formatted_groups = "\n".join(group_lines)
        print(f"  Matched groups:\n\n{formatted_groups}\n")

    def _annotation_is_complete(self, annotation):
        return all(
            annotation[required_attribute] is not None
            for required_attribute in self._required_attributes
        )

    def _handle_reset(self, rule, annotation):
        if rule.get("reset"):
            annotation = dict.fromkeys(annotation, None)
        return annotation

    def _handle_severity(self, rule, annotation):
        severity = rule.get("severity")
        if severity is not None:
            annotation["severity"] = severity
        return annotation

    def _update_annotation(self, annotation, rule, match):
        set_dict = self._default_set_dict.copy()
        set_dict.update(rule.get("set", {}))
        for key, group in set_dict.items():
            if value := match.groups()[group]:
                annotation[key] = value.format(*match.groups())
        return annotation

    def _add_annotation(self, annotation):
        if self._annotation_is_complete(annotation):
            annotation = annotation.copy()
            if annotation not in self._annotations:
                self._annotations.append(annotation)

    def _handle_match(self, match, line, rule):
        if self._debug:
            self._debug_groups(line, match)
        annotation = self._current_annotation
        annotation = self._handle_reset(rule, annotation)
        annotation = self._handle_severity(rule, annotation)
        annotation = self._update_annotation(annotation, rule, match)
        self._add_annotation(annotation)
        self._current_annotation = annotation

    def _handle_rules(self, line):
        for rule in self._rules:
            if match := rule["match_re"].search(line):
                self._handle_match(match, line, rule)

    def _annotate(self, input):
        input = self._decode(input)
        input_lines = input.strip().splitlines()
        self._default_set_dict = self._config.get("set", {})
        self._current_annotation = self._template_annotation.copy()
        for line in input_lines:
            line = line.rstrip("\n")
            self._handle_rules(line)
        return self._annotations
