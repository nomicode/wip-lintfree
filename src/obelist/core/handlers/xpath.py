from lxml import etree

from . import Handler


class XPathHandler(Handler):

    _root_node = None

    def _set_value(self, match, set_dict, key):
        query = set_dict.get(key)
        return None if query is None else match.xpath(query)[0]

    def _annotate(self, input):
        parser = etree.XMLParser(resolve_entities=False)
        self._root_node = etree.fromstring(input, parser)

        def matches_fn(query):
            return self._root_node.xpath(query)

        self._generate_matches(matches_fn)
        return self._annotations
