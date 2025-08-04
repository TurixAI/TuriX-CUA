# --- START OF FILE mac_use/mac/element.py ---
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from functools import cached_property
import logging
logger = logging.getLogger(__name__)
@dataclass
class MacElementNode:
    """Represents a UI element in macOS with enhanced accessibility information"""
    # Required fields
    role: str
    identifier: str
    attributes: Dict[str, Any]
    is_visible: bool
    app_pid: int
    on_screen: bool

    # Optional fields
    children: List['MacElementNode'] = field(default_factory=list)
    parent: Optional['MacElementNode'] = None
    is_interactive: bool = False
    highlight_index: Optional[int] = None
    _element = None  # Store AX element reference

    @property
    def actions(self) -> List[str]:
        """Get the list of available actions for this element."""
        list_actions = self.attributes.get('actions', [])
        return list_actions

    @property
    def enabled(self) -> bool:
        """Check if the element is enabled."""
        return self.attributes.get('enabled', True)

    @property
    def position(self) -> Optional[tuple]:
        """Get the element's position."""
        return self.attributes.get('position')

    @property
    def size(self) -> Optional[tuple]:
        """Get the element's size."""
        return self.attributes.get('size')

    def __repr__(self) -> str:
        """Enhanced string representation including more attributes."""
        role_str = f'<{self.role}'

        # Add important attributes to the string representation
        important_attrs = ['title', 'value', 'description', 'enabled']
        for key in important_attrs:
            if key in self.attributes:
                role_str += f' {key}="{self.attributes[key]}"'

        # Add position and size if available
        if self.position:
            role_str += f' pos={self.position}'
        if self.size:
            role_str += f' size={self.size}'

        role_str += '>'

        # Add status indicators
        extras = []
        if self.is_interactive:
            extras.append('interactive')
            if self.actions:
                extras.append(f'actions={self.actions}')
        if self.highlight_index is not None:
            extras.append(f'highlight:{self.highlight_index}')
        if not self.enabled:
            extras.append('disabled')

        if extras:
            role_str += f' [{", ".join(extras)}]'

        return role_str

    # ------------------------------------------------------------------------
    # INTERNAL: A short, concise element representation (used by the "short" version).
    # ------------------------------------------------------------------------
    def _format_short_element(self) -> str:
        """
        Produce a short, clean summary string for this element:
         - highlight_index or '_' as prefix
         - role
         - if title or description exist, show them
         - location/size in parentheses
         - if interactive, show actions
        """
        # Decide prefix: highlight index or underscore
        prefix = f'{self.highlight_index}' if self.highlight_index is not None else '_'
        # Basic role
        role_part = f'<{self.role}'
        # Possibly add title
        if 'title' in self.attributes:
            role_part += f' title="{self.attributes["title"]}"'
        # Possibly add description
        if 'description' in self.attributes:
            role_part += f' description="{self.attributes["description"]}"'

        # location/size
        pos = self.attributes.get('position')
        siz = self.attributes.get('size')
        if pos and siz:
            role_part += f' pos={pos} size={siz}'

        role_part += '>'

        # If interactive, mention it plus the actions
        extras = []
        if self.is_interactive:
            extras.append('interactive')
            if self.actions:
                extras.append(f'actions={self.actions}')

        if extras:
            role_part += f' [{", ".join(extras)}]'

        return f'{prefix}[:]{role_part}'

    # ------------------------------------------------------------------------
    # 1) The "original" version with more details
    # ------------------------------------------------------------------------
    def _get_visible_clickable_elements_string_short(self) -> str:
        """Convert the UI tree to a string representation focusing on interactive and context elements"""
        formatted_text = []
        def process_node(node: 'MacElementNode', depth: int) -> None:
            # Build attributes string
            if not node.highlight_index or not node.on_screen:
                pass
            elif node.role in ['AXStaticText', 'AXGroup', 'AXImage']:
                pass
            else:
                attrs_str = ''
                important_attrs = ['title', 'value', 'description','position','size']
                # logger.debug(f'Processing node: {node.role} with attributes: {node.attributes}')
                for key in important_attrs:
                    if key in node.attributes:
                        if key == 'position':
                            attrs_str += f' Top left: "{node.attributes[key]}"'
                        else:
                            attrs_str += f'(w,h): "{node.attributes[key]}"'
                if attrs_str != '':
                    formatted_text.append(
                        f'{node.highlight_index}[:]<{node.role}{attrs_str}>'
                    )

            for child in node.children:
                process_node(child, depth + 1)

        process_node(self, 0)
        return '\n'.join(formatted_text)

    # ------------------------------------------------------------------------
    # 2) The "short" version with fewer details
    # ------------------------------------------------------------------------
    def _get_visible_clickable_elements_string_original(self) -> str:
        """
        Short version: 
        Omits duplicates based on (role, description) to reduce length, 
        uses `_format_short_element` for a more condensed view.
        """
        formatted_text = []
        def process_node(node: 'MacElementNode', depth: int) -> None:
            # Build attributes string
            if not node.highlight_index or not node.on_screen:
                pass
            attrs_str = ''
            important_attrs = ['title', 'value', 'description', 'enabled','position','size']
            # logger.debug(f'Processing node: {node.role} with attributes: {node.attributes}')
            for key in important_attrs:
                if key in node.attributes:
                    if key == 'position':
                        attrs_str += f' Top left: "{node.attributes[key]}"'
                    else:
                        attrs_str += f'(w,h): "{node.attributes[key]}"'


            formatted_text.append(
                f'{node.highlight_index}[:]<{node.role}{attrs_str}> [interactive]'
            )
            # Check if this is a context element (non-interactive AXStaticText or read-only AXTextField)
            if (node.role in ['AXStaticText', 'AXTextField'] and 
                  not node.is_interactive and 
                  (node.parent is None or node.parent.role == 'AXWindow' or node.parent.is_interactive)):
                # Context element with "_" index
                formatted_text.append(
                    f'_[:]<{node.role}{attrs_str}> [context]'
                )

            for child in node.children:
                process_node(child, depth + 1)

        process_node(self, 0)
        return '\n'.join(formatted_text)

    def _get_visible_clickable_elements_string(self) -> str:
        def count_tokens(text: str, estimated_tokens_per_character: int = 3) -> int:
            return len(text) // estimated_tokens_per_character
        total_tokens = count_tokens(self._get_visible_clickable_elements_string_original())
        if total_tokens > 10000:
            # Return the short version
            logger.debug('Token count exceeded 10000, Do not use UI')
            return ''
        else:
            # Return the short version
            logger.debug(f'Token count is {total_tokens}, using original version.')
            return self._get_visible_clickable_elements_string_short()
        
    def get_detailed_info(self) -> str:
        """Return a detailed string with all attributes of the element."""
        details =[
            f"Role: {self.role}",
            f"Identifier: {self.identifier}",
            f"Interactive: {self.is_interactive}",
            f"Enabled: {self.enabled}",
            f"Visible: {self.is_visible}"
        ]

        if self.actions:
            details.append(f"Actions: {self.actions}")

        if self.position:
            details.append(f"Position: {self.position}")

        if self.size:
            details.append(f"Size: {self.size}")

        for key, value in self.attributes.items():
            if key not in ['actions', 'enabled', 'position', 'size']:
                details.append(f"{key}: {value}")

        return ", ".join(details)

    def get_detailed_string(self, indent: int = 0) -> str:
        """Recursively build a detailed string representation of the UI tree."""
        spaces = " " * indent
        result = (
            f"{spaces}{self.__repr__()}\n{spaces}Details: {self.get_detailed_info()}"
        )
        for child in self.children:
            result += "\n" + child.get_detailed_string(indent + 2)
        return result

    @cached_property
    def accessibility_path(self) -> str:
        """Generate a unique path to this element including more identifiers."""
        path_components = []
        current = self
        while current.parent is not None:
            role = current.role

            # Add identifiers to make the path more specific
            identifiers = []
            if 'title' in current.attributes:
                identifiers.append(f"title={current.attributes['title']}")
            if 'description' in current.attributes:
                identifiers.append(f"desc={current.attributes['description']}")

            # Count siblings with same role
            siblings = [s for s in current.parent.children if s.role == role]
            if len(siblings) > 1:
                idx = siblings.index(current) + 1
                path_component = f"{role}[{idx}]"
            else:
                path_component = role

            # Add identifiers if available
            if identifiers:
                path_component += f"({','.join(identifiers)})"

            path_components.append(path_component)
            current = current.parent

        path_components.reverse()
        return '/' + '/'.join(path_components)

    def find_element_by_path(self, path: str) -> Optional['MacElementNode']:
        """Find an element using its accessibility path."""
        if self.accessibility_path == path:
            return self
        for child in self.children:
            result = child.find_element_by_path(path)
            if result:
                return result
        return None

    def find_elements_by_action(self, action: str) -> List['MacElementNode']:
        """Find all elements that support a specific action."""
        elements = []
        if action in self.actions:
            elements.append(self)
        for child in self.children:
            elements.extend(child.find_elements_by_action(action))
        return elements
