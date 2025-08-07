from typing import Optional
from typing import List
from pydantic import BaseModel, Field
from src.controller.registry.views import ActionModel

class DoneAction(BaseModel):
	text: str

class InputTextAction(BaseModel):
	text: str
	
class OpenAppAction(BaseModel):
	app_name: str

class AppleScriptAction(BaseModel):
	script: str

class PressAction(BaseModel):
	key: str

class PressCombinedAction(BaseModel):
	key1: str
	key2: str
	key3: Optional[str] = None

class LeftClickPositionAction(BaseModel):
	index: int

class RightClickPositionAction(BaseModel):
	index: int

class MoveToAction(BaseModel):
	position: List[float] = Field(..., description="Coordinates (normalised) [x,y]")

class LeftClickPixel(BaseModel):
    position: List[float] = Field(..., description="Coordinates (normalised) [x,y]")

class RightClickPixel(BaseModel):
    position: List[float] = Field(..., description="Coordinates (normalised) [x,y]")

class ScrollUpAction(BaseModel):
	position: List[float] = Field(..., description="Coordinates (normalised) [x,y] to execute scroll")
	dx: Optional[int] = Field(..., description="Amount to scroll left, between 0 and 25")
	dy: Optional[int] = Field(..., description="Amount to scroll up, between 0 and 25")

class ScrollDownAction(BaseModel):
	position: List[float] = Field(..., description="Coordinates (normalised) [x,y] to execute scroll")
	dx: Optional[int] = Field(..., description="Amount to scroll left, between 0 and 25")
	dy: Optional[int] = Field(..., description="Amount to scroll down, between 0 and 25")

class ExtractAction(BaseModel):
	position1: List[float] = Field(..., description="Coordinates (normalised) [x,y]")

class DragAction(BaseModel):
	position1: List[float] = Field(..., description="Starting Coordinates (normalised) [x,y]")
	position2: List[float] = Field(..., description="Ending Coordinates (normalised) [x,y]")

class NoParamsAction(ActionModel):
	"""
	Simple parameter model requiring no arguments.
	"""
	pass