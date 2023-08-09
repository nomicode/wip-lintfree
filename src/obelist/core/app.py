import os
import pathlib

import sh

import obelist
from .config import Configuration
from .parse import Parser
from obelist import errors


class Application:

    _PKG_CONFIG_DIR = "data/configs"

    _USER_CONFIG_DIR = ".obelist"

    _CONFIG_GLOB = "**/*.yaml"

    _quiet = None
    _debug = None
    _error_on = None
    _write_file = None
    _console = None

    _root_path = None

    _config_search_paths = []

    _configs = []
    _parsers = {}

    _parser = None

    def configure(self, quiet, debug, error_on, write_file, console):
        self._quiet = quiet
        self._debug = debug
        self._error_on = error_on
        self._write_file = write_file
        self._console = console

    def _build_config_search_paths(self, dir_path):
        search_dir = dir_path.joinpath(f"{self._USER_CONFIG_DIR}")
        if not dir_path.samefile(self._root_path):
            parent = dir_path.parent
            yield from self._build_config_search_paths(parent)
        yield search_dir

    def _find_root(self):
        try:
            # pylint: disable=too-many-function-args
            stdout = sh.git("rev-parse", "--git-dir")
            root_dir = str(stdout)
            self._root_path = pathlib.Path(root_dir).parent
        except sh.CommandNotFound:
            self._root_path = pathlib.Path.cwd().root

    def _extend_config_search_path(self, search_path, pwd_path):
        search_path.append(obelist.configs_dir_path)
        self._find_root()
        for path in self._build_config_search_paths(pwd_path):
            search_path.append(path)

    def set_config_search_paths(self, search_path):
        search_path = list(search_path)
        pwd_path = pathlib.Path(".").resolve()
        if not search_path:
            self._extend_config_search_path(search_path, pwd_path)
        for path in reversed(search_path):
            absolute_path = path.resolve()
            self._config_search_paths.append(absolute_path)

    def get_config_search_paths(self, absolute):
        for path in self._config_search_paths:
            if not absolute:
                path = os.path.relpath(path)
            yield path

    def _get_config_files(self):
        for dir_path in self._config_search_paths:
            if dir_path.is_dir():
                yield from dir_path.glob(self._CONFIG_GLOB)

    def _load_config(self, config_path):
        config = Configuration(config_path)
        self._configs.append(config)
        parser = Parser(self, config)
        self._parsers[config.id] = parser

    def load_configs(self):
        for file_path in self._get_config_files():
            self._load_config(file_path)

    def debug(self):
        raise errors.NotImplementedError()

    def _validate(self, config, states):
        if config.valid is not None:
            return states["valid"] if config.valid else states["invalid"]
        else:
            return states["not_validated"]

    def list(self, absolute, states):
        # TODO: Indicate active config when multiple configs share the same ID
        for config in self._configs:
            filename = config.filename
            if not absolute:
                filename = os.path.relpath(filename)
            validity = self._validate(config, states)
            yield config, filename, validity

    def parse(self, parser_id, input, format):
        try:
            self._parser = self._parsers[parser_id]
        except KeyError as err:
            raise errors.NoParserError() from err
        self._parser.parse(input, format, self._debug)

    def read_commands(self, read_file):
        self._parser = Parser(self, None)
        self._parser.read_commands(read_file)

    def print(self, sort_by, before_context, after_context):
        status_code = self._parser.print(
            self._error_on,
            self._write_file,
            sort_by,
            before_context,
            after_context,
        )
        # TODO: Could probably loosen this up so any statement which could
        # evaluate to true will work (perhaps Click can help with this)
        if os.environ.get("OBELIST_NO_ERROR") == "true":
            status_code = 0
        return status_code
