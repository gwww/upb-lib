"""
Base of the UpbDevice and link elements.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar


class Addr:
    """Base representation of an address for UPB devices and links."""

    def __init__(self, network_id: int, upb_id: int, is_link: bool = False):
        self._network_id = network_id
        self._upb_id = upb_id
        self._is_link = is_link
        self._index: str = ""

    @property
    def network_id(self) -> int:
        """Return the network id."""
        return self._network_id

    @property
    def upb_id(self) -> int:
        """Return the device id."""
        return self._upb_id

    @property
    def is_device(self) -> bool:
        """Return the if this is a device."""
        return not self._is_link

    @property
    def is_link(self) -> bool:
        """Return the if this is a link."""
        return self._is_link

    @property
    def index(self) -> str:
        """Return the address in index form."""
        return self._index

    def __str__(self) -> str:
        """Return the address in index form."""
        return str(self._index)


U = TypeVar("U", bound=Addr)


class Element(Generic[U]):
    """Element class"""

    def __init__(self, addr: U, pim):
        self._addr = addr
        self._index = addr.index
        self._pim = pim
        self._observers: list[Callable[[Element, dict[str, Any]], None]] = []
        self._changeset: dict[str, Any] = {}
        self.name: str | None = None

    @property
    def index(self) -> str:
        """Get the index, immutable once class created"""
        return self._index

    @property
    def addr(self) -> U:
        """Get the address."""
        return self._addr

    @property
    def response_addr(self) -> bytearray:
        """Convert network_id and upb_id into bytes used for checking response"""
        return bytearray([self.addr.network_id, self.addr.upb_id])

    def add_callback(self, observer: Callable[[Element, dict[str, Any]], None]) -> None:
        """Callbacks when attribute of element changes"""
        self._observers.append(observer)

    def remove_callback(
        self, observer: Callable[[Element, dict[str, Any]], None]
    ) -> None:
        """Callbacks when attribute of element changes"""
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify(self) -> None:
        """Callbacks when attribute of element changes"""
        for observer in self._observers:
            observer(self, self._changeset)
        self._changeset = {}

    def setattr(
        self, attr: str, new_value: Any, close_the_changeset: bool = True
    ) -> None:
        """If attribute value has changed then set it and call the callbacks"""
        existing_value = getattr(self, attr, None)
        if existing_value != new_value:
            setattr(self, attr, new_value)
            self._changeset[attr] = new_value

        if close_the_changeset and self._changeset:
            self._notify()

    def __str__(self) -> str:
        varlist = {
            k: v
            for (k, v) in vars(self).items()
            if not k.startswith("_") and k != "name"
        }.items()
        # pylint: disable=consider-using-f-string
        varstr = " ".join("{}:{}".format(*item) for item in varlist)
        return f"{self._index} '{self.name}' {varstr}"

    def as_dict(self) -> dict[str, Any]:
        """Package up the public attributes as a dict."""
        attrs = vars(self)
        return {key: attrs[key] for key in attrs if not key.startswith("_")}


T = TypeVar("T", bound=Element)


class Elements(Generic[T]):
    """Base for list of elements."""

    def __init__(self, pim):
        self.pim = pim
        self.elements: dict[str, T] = {}

    def add_element(self, element: T) -> None:
        """Add an element to list of elements."""
        self.elements[element.index] = element

    def connection_status_change(self, _) -> None:
        """Force a callback when the PIM becomes connected/disconnected."""
        for _, element in self.elements.items():
            element._notify()  # pylint: disable=protected-access

    def sync(self) -> None:
        """Should be overridden by derived class."""
        raise NotImplementedError()

    def __iter__(self):
        yield from self.elements

    def __getitem__(self, key) -> Element | None:
        return self.elements.get(key)
