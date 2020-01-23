"""
  Base of the light and link elements.
"""


class Element:
    """Element class"""

    def __init__(self, index, pim):
        self._index = index
        self._pim = pim
        self._callbacks = []
        self._changeset = {}
        self.name = None

    @property
    def index(self):
        """Get the index, immutable once class created"""
        return self._index

    def add_callback(self, callback):
        """Callbacks when attribute of element changes"""
        self._callbacks.append(callback)

    def remove_callback(self, callback):
        """Callbacks when attribute of element changes"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _call_callbacks(self):
        """Callbacks when attribute of element changes"""
        for callback in self._callbacks:
            callback(self, self._changeset)
        self._changeset = {}

    def setattr(self, attr, new_value, close_the_changeset=True):
        """If attribute value has changed then set it and call the callbacks"""
        existing_value = getattr(self, attr, None)
        if existing_value != new_value:
            setattr(self, attr, new_value)
            self._changeset[attr] = new_value

        if close_the_changeset and self._changeset:
            self._call_callbacks()

    def default_name(self, separator="-"):
        """Return a default name for based on class and index of element"""
        return self.__class__.__name__ + "{}{:03d}".format(separator, self._index + 1)

    def is_default_name(self):
        """Check if the name assigned is the default_name"""
        return self.name == self.default_name()

    def __str__(self):
        varlist = {
            k: v
            for (k, v) in vars(self).items()
            if not k.startswith("_") and k != "name"
        }.items()
        varstr = " ".join("%s:%s" % item for item in varlist)
        return "{} '{}' {}".format(self._index, self.name, varstr)

    def as_dict(self):
        """Package up the public attributes as a dict."""
        attrs = vars(self)
        return {key: attrs[key] for key in attrs if not key.startswith("_")}


class Elements:
    """Base for list of elements."""

    def __init__(self, pim):
        self.pim = pim
        self.elements = {}
        self.pim.add_sync_handler(self.sync)

    def add_element(self, index, element):
        self.elements[index] = element

    def __iter__(self):
        for element in self.elements:
            yield element

    def __getitem__(self, key):
        return self.elements[key]
