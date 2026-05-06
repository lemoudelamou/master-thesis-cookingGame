IMAGE_FIELDS = ["openIcon", "cursorBitmap", "additiveOpenIcon", "activeIcon"]

SOUND_FIELDS = ["sound", "activeSound", "openSound", "doneSound", "speech"]

TOOL_FIELDS = ["tool"]

APP_CONFIG = {"page_title": "JSON Assets Checker", "page_icon": "🔍", "layout": "wide"}



# ---------------------------------------------------------------------------
# tasksText.json key patterns
# ---------------------------------------------------------------------------

TASKS_TEXT_KEY_PATTERNS = {
    "titles": r"^desc_[0-9]+[a-zA-Z]*$",
    "descriptions": r"^info_[0-9]+[a-zA-Z]*$",
    "informations": r"^info_[0-9]+[a-zA-Z]*$",
    "feedbacks": r"^feed_[0-9]+[a-zA-Z]*$",
    # "additionals" has no pattern constraint — any string key is valid
}

TASKS_TEXT_KEY_EXAMPLES = {
    "titles": "desc_00, desc_01, desc_24a",
    "descriptions": "info_00, info_01, info_46c",
    "informations": "info_00, info_04",
    "feedbacks": "feed_00, feed_01",
}

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

PROCESS_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Process Schema",
    "description": "Schema for process definitions with tasks and transitions",
    "type": "object",
    "required": ["tasks", "transitions"],
    "properties": {
        "tasks": {
            "type": "array",
            "description": "Array of task items",
            "items": {
                "type": "object",
                "required": ["name", "info", "description", "openIcon"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique identifier/name for the task",
                    },
                    "info": {
                        "type": "string",
                        "description": "Info reference (e.g., 'info_00', 'info_13')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description reference (e.g., 'desc_00', 'desc_13')",
                    },
                    "openIcon": {
                        "type": "string",
                        "description": "Path to the icon displayed when item is open (e.g., '0804/orange')",
                    },
                    "activeIcon": {
                        "type": "string",
                        "description": "Path to the icon displayed when item is active",
                    },
                    "doneIcon": {
                        "type": "string",
                        "description": "Path to the icon displayed when item is done",
                    },
                    "cursorBitmap": {
                        "type": "string",
                        "description": "Path to the cursor bitmap",
                    },
                    "cursorHotspot": {
                        "type": "string",
                        "description": "Cursor hotspot coordinates as space-separated values (e.g., '90 81')",
                    },
                    "CursorHotspot": {
                        "type": "string",
                        "description": "Alternative cursor hotspot (capitalized version, legacy)",
                    },
                    "hoverBitmap": {
                        "type": "string",
                        "description": "Bitmap to display on hover",
                    },
                    "canHaveAlternativeDonePosition": {
                        "type": "string",
                        "pattern": "^[01]$",
                        "description": "Whether item can have alternative done position (0 or 1)",
                    },
                    "customPositionOffsetMouse": {
                        "type": "string",
                        "description": "Custom position offset for mouse as space-separated values (e.g., '10 33')",
                    },
                    "customExtentOffsetMouse": {
                        "type": "string",
                        "description": "Custom extent offset for mouse as space-separated values (e.g., '-20 -70')",
                    },
                    "openPosition": {
                        "type": "string",
                        "enum": [
                            "stoveLeftTop",
                            "stoveLeftBottom",
                            "stoveRightTop",
                            "stoveRightBottom",
                            "countertopLeftTop",
                            "countertopLeftBottom",
                            "countertopRightTop",
                            "countertopRightBottom",
                            "oven",
                            "cuttingboard",
                            "sink",
                        ],
                        "description": "Position where item opens",
                    },
                    "donePosition": {
                        "type": "string",
                        "enum": [
                            "stoveLeftTop",
                            "stoveLeftBottom",
                            "stoveRightTop",
                            "stoveRightBottom",
                            "countertopLeftTop",
                            "countertopLeftBottom",
                            "countertopRightTop",
                            "countertopRightBottom",
                            "oven",
                            "cuttingboard",
                            "sink",
                        ],
                        "description": "Position when item is done",
                    },
                    "activePosition": {
                        "type": "string",
                        "enum": [
                            "stoveLeftTop",
                            "stoveLeftBottom",
                            "stoveRightTop",
                            "stoveRightBottom",
                            "countertopLeftTop",
                            "countertopLeftBottom",
                            "countertopRightTop",
                            "countertopRightBottom",
                            "oven",
                            "cuttingboard",
                            "sink",
                        ],
                        "description": "Position when item is active",
                    },
                    "openSound": {
                        "type": "string",
                        "description": "Sound to play when item opens",
                    },
                    "doneSound": {
                        "type": "string",
                        "description": "Sound to play when item is done",
                    },
                    "activeSound": {
                        "type": "string",
                        "description": "Sound to play when item is active",
                    },
                    "activeTime": {
                        "type": "string",
                        "pattern": "^[0-9]+$",
                        "description": "Time in active state in seconds (numeric string)",
                    },
                    "activeToDone": {
                        "type": "string",
                        "pattern": "^[01]$",
                        "description": "Whether to automatically transition from active to done (0 or 1)",
                    },
                    "userMoveActiveToDonePosition": {
                        "type": "string",
                        "pattern": "^[01]$",
                        "description": "Whether user can move from active to done position (0 or 1)",
                    },
                    "unopenedToOpen": {
                        "type": "string",
                        "pattern": "^[01]$",
                        "description": "Whether to transition from unopened to open state (0 or 1)",
                    },
                    "openPreview": {
                        "type": "string",
                        "description": "Preview image/icon for unopened state",
                    },
                    "speech": {
                        "type": "string",
                        "description": "Speech/audio reference",
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Feedback reference (e.g., 'feed_00')",
                    },
                },
                "additionalProperties": False,
            },
        },
        "transitions": {
            "type": "array",
            "description": "Array of transitions between tasks",
            "items": {
                "type": "object",
                "required": ["name", "parent", "child"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique identifier/name for the transition (e.g., 'transition (move_00)')",
                    },
                    "parent": {
                        "type": "string",
                        "description": "Name of the parent/source task",
                    },
                    "child": {
                        "type": "string",
                        "description": "Name of the child/target task",
                    },
                    "tool": {
                        "type": "string",
                        "description": "Tool required for transition (e.g., 'watertap', 'messer', 'loeffel', 'schneebesen')",
                    },
                    "sound": {
                        "type": "string",
                        "description": "Sound effect to play during transition",
                    },
                    "automatic": {
                        "type": "string",
                        "pattern": "^[01]$",
                        "description": "Whether this transition is automatic (0 or 1)",
                    },
                    "mandatory": {
                        "type": "string",
                        "pattern": "^[01]$",
                        "description": "Whether this transition is mandatory (0 or 1)",
                    },
                    "lob": {
                        "type": "string",
                        "pattern": "^[0-9]+$",
                        "description": "Praise/reward level (numeric string)",
                    },
                    "minigameAction": {
                        "type": "string",
                        "description": "Type of minigame action (e.g., 'circlePositive', 'topBottom')",
                    },
                    "minigameMaxTime": {
                        "type": "string",
                        "pattern": "^[0-9]+$",
                        "description": "Maximum time for minigame in seconds (numeric string)",
                    },
                    "minigamePosition": {
                        "type": "string",
                        "description": "Position where minigame occurs (e.g., 'cuttingboard', 'stoveRightBottom', 'countertopLeftTop')",
                    },
                    "minigameMaxScore": {
                        "type": "string",
                        "pattern": "^[0-9]+$",
                        "description": "Maximum score for minigame (numeric string)",
                    },
                    "additiveOpenIcon": {
                        "type": "string",
                        "description": "Additional icon to display during transition (e.g., '0804/additive_honig')",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


TASKS_TEXT_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Task Texts Schema",
    "description": "Schema for task text definitions including titles, descriptions, informations, feedbacks, and additional texts",
    "type": "object",
    "required": ["titles", "descriptions", "informations", "feedbacks", "additionals"],
    "properties": {
        "titles": {
            "type": "array",
            "description": "Array of title text entries",
            "items": {
                "type": "object",
                "required": ["key", "value"],
                "properties": {
                    "key": {
                        "type": "string",
                        "pattern": "^desc_[0-9]+[a-zA-Z]*$",
                        "description": "Description key identifier (e.g., 'desc_00', 'desc_01', 'desc_24a')",
                    },
                    "value": {"type": "string", "description": "The title text value"},
                },
                "additionalProperties": False,
            },
        },
        "descriptions": {
            "type": "array",
            "description": "Array of description text entries",
            "items": {
                "type": "object",
                "required": ["key", "value"],
                "properties": {
                    "key": {
                        "type": "string",
                        "pattern": "^info_[0-9]+[a-zA-Z]*$",
                        "description": "Info key identifier (e.g., 'info_00', 'info_01', 'info_46c')",
                    },
                    "value": {
                        "type": "string",
                        "description": "The description text value",
                    },
                },
                "additionalProperties": False,
            },
        },
        "informations": {
            "type": "array",
            "description": "Array of information reference entries",
            "items": {
                "type": "object",
                "required": ["key", "value"],
                "properties": {
                    "key": {
                        "type": "string",
                        "pattern": "^info_[0-9]+[a-zA-Z]*$",
                        "description": "Info key identifier (e.g., 'info_00', 'info_04')",
                    },
                    "value": {
                        "type": "string",
                        "description": "Reference value or additional information identifier",
                    },
                },
                "additionalProperties": False,
            },
        },
        "feedbacks": {
            "type": "array",
            "description": "Array of feedback text entries",
            "items": {
                "type": "object",
                "required": ["key", "value"],
                "properties": {
                    "key": {
                        "type": "string",
                        "pattern": "^feed_[0-9]+[a-zA-Z]*$",
                        "description": "Feedback key identifier (e.g., 'feed_00', 'feed_01')",
                    },
                    "value": {
                        "type": "string",
                        "description": "The feedback text value",
                    },
                },
                "additionalProperties": False,
            },
        },
        "additionals": {
            "type": "array",
            "description": "Array of additional text entries for UI labels and misc text",
            "items": {
                "type": "object",
                "required": ["key", "value"],
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Additional text key identifier (e.g., 'ToolsText', 'Text_Tipps')",
                    },
                    "value": {
                        "type": "string",
                        "description": "The additional text value",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}
