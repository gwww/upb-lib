"""
  Base of the UpbDevice and link elements.
"""


class Addr:
    """Base representation of an address for UPB devices and links."""

    def __init__(self, network_id, upb_id, is_link=False):
        self._network_id = network_id
        self._upb_id = upb_id
        self._is_link = is_link
        self._index = None

    @property
    def network_id(self):
        """Return the network id."""
        return self._network_id

    @property
    def upb_id(self):
        """Return the device id."""
        return self._upb_id

    @property
    def is_device(self):
        """Return the if this is a device."""
        return not self._is_link

    @property
    def is_link(self):
        """Return the if this is a link."""
        return self._is_link

    @property
    def index(self):
        """Return the address in index form."""
        return self._index

    def __str__(self):
        """Return the address in index form."""
        return str(self._index)


class Element:
    """Element class"""

    def __init__(self, addr, pim):
        self._addr = addr
        self._index = addr.index
        self._pim = pim
        self._callbacks = []
        self._changeset = {}
        self.name = None

    @property
    def index(self):
        """Get the index, immutable once class created"""
        return self._index

    @property
    def addr(self):
        """Get the address."""
        return self._addr

    def add_callback(self, callback):
        """Callbacks when attribute of element changes"""
        self._callbacks.append(callback)

    def remove_callback(self, callback):
        """Callbacks when attribute of element changes"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def call_callbacks(self):
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
            self.call_callbacks()

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

    def add_element(self, element):
        """Add an element to list of elements."""
        self.elements[element.index] = element

    def connection_status_change(self, _):
        """Force a callback when the PIM becomes connected/disconnected."""
        for _, element in self.elements.items():
            element.call_callbacks()

    def sync(self):
        """Should be overridden by derived class."""
        raise NotImplementedError()

    def __iter__(self):
        for element in self.elements:
            yield element

    def __getitem__(self, key):
        return self.elements.get(key)
