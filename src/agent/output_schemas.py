# output_schemas.py
from typing import Any, Dict

class OutputSchemas:
    AGENT_SCHEMA = {
        "type": "object",
        "properties": {
            "action": {
                "type": "array",
                "minItems": 0,
                "default": [ { "wait": {} } ], 
                "items": {
                    "type": "object",
                    "properties": {
                    # ----- task finished -----
                    "done": {"type": "object",
                        "properties": {"text": {"type": "string"}}},

                    # ----- typing -----
                    "input_text": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"]
                    },

                    # ----- open app -----
                    "open_app": {
                        "type": "object",
                        "properties": {"app_name": {"type": "string"}},
                        "required": ["app_name"]
                    },

                    # ----- AppleScript -----
                    "run_apple_script": {
                        "type": "object",
                        "properties": {"script": {"type": "string"}},
                        "required": ["script"]
                    },

                    # ----- hotkeys -----
                    "Hotkey": {
                        "type": "object",
                        "properties": {"key": {"type": "string"}},
                        "required": ["key"]
                    },
                    "multi_Hotkey": {
                        "type": "object",
                        "properties": {
                            "key1": {"type": "string"},
                            "key2": {"type": "string"},
                            "key3": {"type": "string"},
                        },
                        "required": ["key1", "key2"]
                    },

                    # ----- clicks -----
                    "RightSingle": {
                        "type": "object",
                        "properties": {
                            "position": {
                                "type": "array",
                                "items": {"type": "number"},
                            }
                        },
                        "required": ["position"]
                    },
                    "Click": {
                        "type": "object",
                        "properties": {
                            "position": {"type": "array", "items": {"type": "number"}}
                        },
                        "required": ["position"]
                    },

                    # ----- drag -----
                    "Drag": {
                        "type": "object",
                        "properties": {
                            "position1": {"type": "array", "items": {"type": "number"}},
                            "position2": {"type": "array", "items": {"type": "number"}},
                        },
                        "required": ["position1", "position2"]
                    },

                    # ----- move mouse -----
                    "move_mouse": {
                        "type": "object",
                        "properties": {
                            "position": {"type": "array", "items": {"type": "number"}}
                        },
                        "required": ["position"]
                    },

                    # ----- scrolling -----
                    "scroll_up": {
                        "type": "object",
                        "properties": {
                            "position": {"type": "array", "items": {"type": "number"}},
                            "dx": {"type": "number"},
                            "dy": {"type": "number"},
                        },
                        "required": ["position"]
                    },
                    "scroll_down": {
                        "type": "object",
                        "properties": {
                            "position": {"type": "array", "items": {"type": "number"}},
                            "dx": {"type": "number"},
                            "dy": {"type": "number"},
                        },
                        "required": ["position"]
                    },

                    # ----- memory + wait -----
                    "record_info": {"type": "object",
                        "properties": {"text": {"type": "string"}}},
                    "wait": {"type": "object",
                        "properties": {"text": {"type": "string"}}},
                },

                    }
                },

            "current_state": {
                "type": "object",
                "properties": {
                    "evaluation_previous_goal": {"type": "string"},
                    "next_goal": {"type": "string"},
                    "information_stored": {"type": "string"}
                },
                "required": [
                    "evaluation_previous_goal",
                    "next_goal",
                    "information_stored"
                ]
            }
        },
        "required": [
            "action",
            "current_state"
        ]
    }

    AGENT_RESPONSE_FORMAT = {
        "type": "json_schema",
        "json_schema": {
            "name": "agent_step_output",
            "strict": True,
            "schema": AGENT_SCHEMA
        }
    }

