from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel


@dataclass
class WindowsElementModel:
    """Windows-specific element model"""
    element_id: int
    role: str
    title: str
    value: str
    description: str
    position: tuple
    size: tuple
    focused: bool
    enabled: bool
    selected: bool
    
    def to_dict(self) -> dict:
        return {
            'element_id': self.element_id,
            'role': self.role,
            'title': self.title,
            'value': self.value,
            'description': self.description,
            'position': self.position,
            'size': self.size,
            'focused': self.focused,
            'enabled': self.enabled,
            'selected': self.selected
        }


class WindowsAction(BaseModel):
    """Windows-specific action model"""
    action: str
    coordinate: Optional[tuple] = None
    text: Optional[str] = None
    element_id: Optional[int] = None
    description: Optional[str] = None
