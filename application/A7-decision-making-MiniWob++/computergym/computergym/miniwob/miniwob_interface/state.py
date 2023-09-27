import re
from xml import dom

from .utils import Phrase


class MiniWoBState(object):
    """MiniWoB state.

    Warning: The return types might be changed in the future!!!
    """

    # Task dimensions
    HEIGHT = ROWS = 210
    WIDTH = COLS = 160
    PROMPT_HEIGHT = PROMPT_ROWS = 50

    def __init__(self, utterance, fields, dom_info, html_body, html_extra):
        """Initialize a MiniWoBState.

        Args:
            utterance (unicode)
            fields (Fields)
            dom_info (dict)
        """
        self.html_body = html_body
        self.html_extra = html_extra

        ################
        # Parse utterance
        assert isinstance(utterance, str)
        self._phrase = Phrase(utterance)
        self._fields = fields
        ################
        # Store DOM
        self._dom_elements = []
        if not dom_info:
            self._root_dom = None
        else:
            self._root_dom = DOMElement(
                dom_info, parent=None, dom_elements=self._dom_elements
            )
        ################
        # Screenshot (None by default)
        self._screenshot = None

    @property
    def utterance(self):
        """Task utterance.

        Returns:
            unicode
        """
        return self._phrase.text

    @property
    def phrase(self):
        """The Phrase object of the utterance.

        Returns:
            Phrase
        """
        return self._phrase

    @property
    def tokens(self):
        """Tokens.

        Returns
            list[unicode]
        """
        return list(self._phrase.tokens)

    def detokenize(self, start, end):
        """Return the substring of the original string that corresponds
        to tokens[start:end].

        Args:
            start (int)
            end (int)
        Returns:
            unicode
        """
        return self._phrase.detokenize(start, end)

    @property
    def fields(self):
        """Key-value fields extracted from the utterance.

        Returns:
            Fields
        """
        return self._fields

    @property
    def dom(self):
        """The root DOM structure.

        Returns:
            DOMElement
        """
        if not self._root_dom:
            raise ValueError("without_DOM is not True")
        return self._root_dom

    @property
    def dom_elements(self):
        """List of all DOM elements, flattened.

        Returns:
            list[DOMElement]
        """
        return self._dom_elements

    def __str__(self):
        return "MiniWoBState(utterance: {})".format(repr(self.utterance))

    __repr__ = __str__

    def set_screenshot(self, pil_image):
        """Add screenshot to the state.

        Args:
            pil_image (PIL Image)
        """
        self._screenshot = pil_image

    @property
    def screenshot(self):
        """Return screenshot, or None if not exist.

        Returns:
            PIL Image or None
        """
        return self._screenshot


class DOMElement(object):
    """Encapsulate the DOM element."""

    def __init__(self, raw_dom, parent=None, dom_elements=None):
        """Create a new DOMElement based on the data from getDOMInfo in JavaScript.

        Args:
            raw_dom (dict): A dict with values from getDOMInfo in JavaScript.
            parent (DOMElement|None): the parent DOMElement, or None
            dom_elements (list|None): If specified, append this DOMElement
                object to the list
        """
        self._parent = parent
        self._tag = raw_dom["tag"].lower()
        self._left = raw_dom["left"]
        self._top = raw_dom["top"]
        self._width = raw_dom["width"]
        self._height = raw_dom["height"]
        self._ref = raw_dom.get("ref")
        if self.tag == "t":
            self._ref = None  # ignore refs for text, since they are unreliable
        if "text" in raw_dom:
            self._text = str(raw_dom["text"])
        else:
            self._text = None
        self._value = raw_dom.get("value")
        self._id = raw_dom.get("id")
        classes = raw_dom.get("classes", "TEXT_CLASS")
        if isinstance(classes, dict):
            classes = "SVG_CLASS"
        elif classes == "":
            classes = "NO_CLASS"
        self._classes = classes
        self._bg_color = self._rgba_str_to_floats(raw_dom.get("bgColor"))
        self._fg_color = self._rgba_str_to_floats(raw_dom.get("fgColor"))
        self._focused = raw_dom.get("focused", False)
        self._tampered = raw_dom.get("tampered", False)
        self._targeted = raw_dom.get("recordingTarget", False)
        # Recurse on the children
        self._children = []

        for raw_child in raw_dom["children"]:
            self._children.append(
                DOMElement(raw_child, parent=self, dom_elements=dom_elements)
            )
        # Fix a bug where sometimes children are created even though all children are <t>
        # (which will incorrectly make this element a non-leaf and thus unclickable)
        if self._children and all(child.tag == "t" for child in self._children):
            self._text = " ".join(child.text for child in self._children)
            self._children = []
        # Add to the collection
        if dom_elements is not None:
            dom_elements.append(self)

    def __eq__(self, other):
        if not isinstance(other, DOMElement):
            return False
        return self.ref == other.ref

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_dict(self):
        return {
            "tag": self.tag,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "text": self.text,
            "value": self.value,
            "id": self.id,
            "classes": self.classes,
        }

    @property
    def tag(self):
        """lowercased tag name (str).

        For <input> tag, also append the input type (e.g., "input_checkbox").
        For Text node, the tag is "t".
        """
        return self._tag

    @property
    def left(self):
        """Left coordinate (float)."""
        return self._left

    @property
    def top(self):
        """Top coordinate (float)."""
        return self._top

    @property
    def width(self):
        """Width of the element (float)."""
        return self._width

    @property
    def height(self):
        """Height of the element (float)."""
        return self._height

    @property
    def right(self):
        """Right coordinate (float)."""
        return self._left + self._width

    @property
    def bottom(self):
        """Bottom coordinate (float)."""
        return self._top + self._height

    @property
    def ref(self):
        """Reference index (int).
        The ref is positive for normal elements and negative for text nodes.
        - Within the same episode, the ref of a DOM element remains the same
        - Exception: text nodes get a different ref at every time step
        - Ref number restarts at the beginning of each episode
        """
        return self._ref

    @property
    def text(self):
        """Text content of the element (unicode).
        For non-leaf nodes, return None.
        """
        return self._text

    @property
    def value(self):
        """For input elements, return the value.
        - For checkbox and radio, return whether the element is selected (bool)
        - Otherwise, return the text inside the input (unicode)
        """
        return self._value

    @property
    def id(self):
        """Return the DOM id attribute (str), or an empty string."""
        return self._id

    @property
    def classes(self):
        """Return the DOM class attribute (str), or an empty string.
        Multiple classes are separated by spaces.
        """
        return self._classes

    @property
    def bg_color(self):
        """Return the background color rgba (float, float, float, float)."""
        return self._bg_color

    @property
    def fg_color(self):
        """Return the foreground color rgba (float, float, float, float)."""
        return self._fg_color

    @property
    def focused(self):
        """Return whether the element is being focused on (bool)."""
        return self._focused

    @property
    def tampered(self):
        """Return whether the element has been clicked on in this episode (bool)."""
        return self._tampered

    @property
    def targeted(self):
        """In a recorded demonstration, return whether the element is the target
        of an event (bool).
        """
        return self._targeted

    @property
    def is_leaf(self):
        """Return whether this is a leaf element (bool)."""
        return self._text is not None

    @property
    def children(self):
        """Return the list of children (list[DOMElement])."""
        return self._children

    @property
    def parent(self):
        """Return the parent (DOMElement)."""
        return self._parent

    @property
    def ancestor_path(self):
        """Returns the path from root to self in a list, starting with root
        (list[DOMElement]).
        """
        path = []
        curr = self
        while curr.parent:
            path.append(curr)
            curr = curr.parent
        return list(reversed(path))

    @property
    def depth(self):
        """Depth in the DOM tree (root is 1). (int)"""
        return len(self.ancestor_path)

    def __str__(self):
        if self.text:
            text = self.text
            text = text[:20] + "..." if len(text) > 20 else text
            text_str = " text={}".format(repr(text))
        else:
            text_str = ""

        value_str = " value={}".format(self.value) if self.value is not None else ""
        classes_str = " classes=[{}]".format(self.classes)
        num_children = len(self.children)
        children_str = " children={}".format(num_children) if num_children != 0 else ""

        return "[{ref}] {tag} @ ({left}, {top}){text}{value}{classes}{children}".format(
            ref=self.ref,
            tag=self.tag,
            left=round(self.left, 2),
            top=round(self.top, 2),
            text=text_str,
            value=value_str,
            classes=classes_str,
            children=children_str,
        )

    __repr__ = __str__

    def visualize(self, join=True):
        """Return a string visualizing the tree structure."""
        lines = []
        lines.append("- {}".format(self))
        for i, child in enumerate(self.children):
            if isinstance(child, str):
                child = child[:20] + "..." if len(child) > 20 else child
                lines.append('  |- "{}"'.format(child))
            else:
                for j, line in enumerate(child.visualize(join=False)):
                    prefix = "   " if (i == len(self.children) - 1 and j) else "  |"
                    lines.append(prefix + line)
        return "\n".join(lines) if join else lines

    def lca(self, other):
        """Returns the least common ancestor of two DOMElement (the node with
        greatest depth that is an ancestor of self and other).

        Args:
            other (DOMElement)

        Returns:
            DOMElement
        """
        # One is kth deg grandparent of other
        if self in other.ancestor_path:
            return self
        elif other in self.ancestor_path:
            return other

        # Find the first spot at which the ancestor paths diverge
        for i, (self_ancestor, other_ancestor) in enumerate(
            zip(self.ancestor_path, other.ancestor_path)
        ):
            if self_ancestor != other_ancestor:
                return self.ancestor_path[i - 1]

        raise ValueError(
            (
                "{} is not in the same DOM tree as {}\n\nself tree: {}\n\n"
                "other tree: {}"
            ).format(self, other, self.visualize(), other.visualize())
        )

    def diff(self, other_dom):
        """Traverses the two DOM trees in the same order and returns all the
        elements that differ between the two in any of the following ways:
            - ref
            - text
            - tampered
            - value
            - left, top, width, height
            - classes
            - tag
            - fg_color, bg_color
            - is_leaf

        Args:
            other_dom (DOMElement)

        Returns:
            list[DOMElement]: the elements that differ (elements that do not
            exist in the other tree count as differing)

        NOTE:
            If two DOMElements have same ref but differ on properties, only ONE
            of them is added to the list, otherwise, both.

        NOTE:
            Compares the first child against first child, second child against
            second, and so on...
        """

        def element_diff(first, second, l):
            """Diffs two DOMElements, and adds them to list l if they differ."""
            # Base cases
            if second is None:
                l.append(first)
                for child in first.children:
                    element_diff(child, None, l)
                return
            elif first is None:
                l.append(second)
                for child in second.children:
                    element_diff(child, None, l)
                return

            if first.ref != second.ref:
                l.append(first)
                l.append(second)
            else:
                if (
                    first.text != second.text
                    or first.tampered != second.tampered
                    # or first.focused != second.focused
                    or first.value != second.value
                    # or first.left != second.left
                    # or first.top != second.top
                    or first.width != second.width
                    or first.height != second.height
                    or first.classes != second.classes
                    or first.tag != second.tag
                    or first.fg_color != second.fg_color
                    or first.bg_color != second.bg_color
                    or first.is_leaf != second.is_leaf
                ):
                    l.append(first)

            # Pad the children with None and diff them
            first_children = list(first.children)  # Make copy to not trash old
            second_children = list(second.children)
            if len(first_children) < len(second_children):
                first_children += [None] * (len(second_children) - len(first_children))
            elif len(first_children) > len(second_children):
                second_children += [None] * (len(first_children) - len(second_children))
            for first_child, second_child in zip(first_children, second_children):
                element_diff(first_child, second_child, l)

        different_elements = []
        element_diff(self, other_dom, different_elements)
        return different_elements

    def _rgba_str_to_floats(self, rgba):
        """Takes a string of the form rgb(?, ?, ?) or rgba(?, ?, ?, ?)
        and extracts the rgba values normalized between 0 and 1.

        NOTE: If rgba is None, returns white (1.0, 1.0, 1.0, 1.0).
        NOTE: If only rgb is passed, assumes a = 100

        Args:
            rgba (string)

        Returns:
            (float, float, float, float): rgba
        """
        if rgba is None:  # Assume is white
            return 1.0, 1.0, 1.0, 1.0

        if "rgba" in rgba:
            m = re.search(r"rgba\(([0-9.]+), ([0-9.]+), ([0-9.]+), ([0-9.]+)\)", rgba)
            a = float(m.group(4))
        else:
            m = re.search(r"rgb\(([0-9.]+), ([0-9.]+), ([0-9.]+)\)", rgba)
            a = 1.0
        return (
            float(m.group(1)) / 255,
            float(m.group(2)) / 255,
            float(m.group(3)) / 255,
            a,
        )
