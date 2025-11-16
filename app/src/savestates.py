import uuid
import json
from enum import Enum
from datetime import datetime

loadedCases = []
activeCase: int = 0


class Side(Enum):
    """
    Enum representing the two possible sides in a court case.
    """
    PROSECUTION = "prosecution"
    DEFENSE = "defense"


class Witness:
    """
    Represents a witness participating in the court case.

    Attributes:
        witness_id (str): Unique identifier for the witness.
        name (str): The name of the witness.
    """

    def __init__(self, name: str, witness_id=None):
        """
        Initialize a Witness instance.

        Args:
            name (str): Witness name.
            witness_id (str, optional): Existing UUID. Generated if not provided.
        """
        self.witness_id = witness_id or str(uuid.uuid4())
        self.name = name

    def __eq__(self, value: object, /) -> bool:
        """
        Compare witness equality based on name.

        Args:
            value (object): Value to compare to.

        Returns:
            bool: True if the value equals the witness name.
        """
        return value == self.name

    def to_dict(self):
        """
        Convert the witness to a dictionary.

        Returns:
            dict: Dictionary containing witness data.
        """
        return {
            "witness_id": self.witness_id,
            "name": self.name
        }

    @staticmethod
    def from_dict(data: dict):
        """
        Reconstruct a Witness from a dictionary.

        Args:
            data (dict): Dictionary containing witness information.

        Returns:
            Witness: The reconstructed Witness object.
        """
        return Witness(
            name=data["name"],
            witness_id=data["witness_id"]
        )


class TimelineEventType(Enum):
    """
    Enum defining the types of events that may occur in the court timeline.
    """
    OPENING = "opening_statement"
    CLOSING = "closing_argument"
    OBJECTION = "objection"
    RULING = "ruling"
    STATEMENT = "statement"
    GENERAL = "general"


class TimelineEvent:
    """
    Represents a single event in a court case timeline.

    Attributes:
        event_id (str): Unique event identifier.
        timestamp (str): ISO timestamp of event creation.
        speaker (str): Who performed the event.
        type (TimelineEventType): The type of event.
        content (str): The text/content of the event.
    """

    def __init__(self, speaker: str, event_type: TimelineEventType, content: str,
                 event_id=None, timestamp=None):
        """
        Initialize a TimelineEvent.

        Args:
            speaker (str): Entity speaking.
            event_type (TimelineEventType): Category of event.
            content (str): Main event text.
            event_id (str, optional): UUID of event. Generated if not given.
            timestamp (str, optional): Event timestamp. Generated if not given.
        """
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now().isoformat()
        self.speaker = speaker
        self.type = event_type
        self.content = content

    def to_dict(self):
        """
        Convert event to a dictionary.

        Returns:
            dict: Serialized event information.
        """
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "speaker": self.speaker,
            "type": self.type.name,
            "content": self.content
        }

    @staticmethod
    def from_dict(data: dict):
        """
        Rebuild a TimelineEvent from a dictionary.

        Args:
            data (dict): Event dictionary.

        Returns:
            TimelineEvent: Reconstructed event instance.
        """
        return TimelineEvent(
            speaker=data["speaker"],
            event_type=TimelineEventType[data["type"]],
            content=data["content"],
            event_id=data["event_id"],
            timestamp=data["timestamp"]
        )


class Court:
    """
    Represents a full court case, containing metadata, participants,
    witnesses, and the full timeline of events.

    Attributes:
        uuid (str): Unique case identifier.
        created (datetime): Timestamp of case creation.
        case_title (str): Title of the case.
        description (str): Case description.
        judge (str): Judge name.
        prosecution_name (str): Prosecution representative.
        defense_name (str): Defense representative.
        playerSide (Side): The player's role.
        witnesses (dict[str, Witness]): All witnesses in the case.
        timeline (list[TimelineEvent]): Timeline of events in order.
    """

    def __init__(self, case_title,
                 description, judge_name,
                 prosecution_name, defendant_name,
                 side,
                 uuid_str=None, created=None) -> None:
        """
        Initialize a Court instance.

        Args:
            case_title (str): The case's title.
            description (str): Description/background story.
            judge_name (str): Name of the judge.
            prosecution_name (str): Prosecution representative name.
            defendant_name (str): Defense representative name.
            side (Side): The player's side (PROSECUTION/DEFENSE).
            uuid_str (str, optional): Existing UUID if loading case.
            created (datetime, optional): Timestamp of creation.
        """

        self.uuid = uuid_str or str(uuid.uuid4())
        self.created = created or datetime.now()

        self.case_title: str = case_title
        self.description: str = description

        self.judge: str = judge_name
        self.prosecution_name: str = prosecution_name
        self.defense_name: str = defendant_name

        self.playerSide: Side = side

        self.witnesses: dict[str, Witness] = {}
        self.timeline: list[TimelineEvent] = []

    def validateSpeaker(self, speaker: str):
        """
        Validate that a speaker is permitted (must be judge, prosecution,
        defense, or a registered witness).

        Args:
            speaker (str): Name to validate.

        Raises:
            IndexError: If the speaker does not exist.
        """
        if speaker not in self.witnesses and \
           speaker != self.judge and \
           speaker != self.prosecution_name and \
           speaker != self.defense_name:
            raise IndexError("Speaker must be a Witness, Judge, Prosecution, or Defense")

    def addEvent(self, speaker: str, event_type: str, content: str):
        """
        Add a timeline event to the case.

        Args:
            speaker (str): Entity performing the event.
            event_type (str): Event type name (must match TimelineEventType key).
            content (str): Event text.
        """
        self.timeline.append(TimelineEvent(speaker, TimelineEventType[event_type], content))

    def to_dict(self):
        """
        Convert the court state into a dictionary.

        Returns:
            dict: Serialized case information.
        """
        return {
            "uuid": self.uuid,
            "created": self.created.isoformat(),

            "case_title": self.case_title,
            "description": self.description,

            "judge": self.judge,
            "prosecution_name": self.prosecution_name,
            "defense_name": self.defense_name,
            "playerSide": self.playerSide.name,

            "witnesses": {
                name: witness.to_dict()
                for name, witness in self.witnesses.items()
            },

            "timeline": [event.to_dict() for event in self.timeline]
        }

    def to_json(self, indent=4):
        """
        Convert the case to a JSON string.

        Args:
            indent (int): Pretty-print indentation.

        Returns:
            str: JSON-encoded case.
        """
        return json.dumps(self.to_dict(), indent=indent)

    @staticmethod
    def from_dict(data: dict):
        """
        Reconstruct a Court object from a dictionary.

        Args:
            data (dict): Serialized case structure.

        Returns:
            Court: Reconstructed Court instance.
        """
        court = Court(
            case_title=data["case_title"],
            description=data["description"],
            judge_name=data["judge"],
            prosecution_name=data["prosecution_name"],
            defendant_name=data["defense_name"],
            side=Side[data["playerSide"]],
            uuid_str=data["uuid"],
            created=datetime.fromisoformat(data["created"])
        )

        for name, wdata in data["witnesses"].items():
            court.witnesses[name] = Witness.from_dict(wdata)

        for ev_dict in data["timeline"]:
            court.timeline.append(TimelineEvent.from_dict(ev_dict))

        return court

    @staticmethod
    def from_json(json_string: str):
        """
        Reconstruct a Court object from a JSON string.

        Args:
            json_string (str): Serialized JSON case file.

        Returns:
            Court: Reconstructed Court instance.
        """
        data = json.loads(json_string)
        return Court.from_dict(data)
