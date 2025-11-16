import uuid
import json
from enum import Enum
from datetime import datetime

loadedCases = []

# index of loadedCases that is active right now
activeCase: int = 0

class Side(Enum):
    PROSECUTION = "prosecution"
    DEFENSE = "defense"


class Witness:
    def __init__(self, name: str, witness_id=None):
        self.witness_id = witness_id or str(uuid.uuid4())
        self.name = name

    def __eq__(self, value: object, /) -> bool:
        return value == self.name

    def to_dict(self):
        return {
            "witness_id": self.witness_id,
            "name": self.name
        }

    @staticmethod
    def from_dict(data: dict):
        return Witness(
            name=data["name"],
            witness_id=data["witness_id"]
        )


class TimelineEventType(Enum):
    OPENING = "opening_statement"
    CLOSING = "closing_argument"
    OBJECTION = "objection"
    RULING = "ruling"
    STATEMENT = "statement"
    GENERAL = "general"


class TimelineEvent:
    def __init__(self, speaker: str, event_type: TimelineEventType, content: str,
                 event_id=None, timestamp=None):

        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now().isoformat()
        self.speaker = speaker
        self.type = event_type
        self.content = content

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "speaker": self.speaker,
            "type": self.type.name,
            "content": self.content
        }

    @staticmethod
    def from_dict(data: dict):
        return TimelineEvent(
            speaker=data["speaker"],
            event_type=TimelineEventType[data["type"]],
            content=data["content"],
            event_id=data["event_id"],
            timestamp=data["timestamp"]
        )


class Court:
    def __init__(self, case_title,
                 description, judge_name,
                 prosecution_name, defendant_name,
                 side,
                 uuid_str=None, created=None) -> None:

        # metadata
        self.uuid = uuid_str or str(uuid.uuid4())
        self.created = created or datetime.now()

        # case information
        self.case_title: str = case_title
        self.description: str = description

        # participants
        self.judge: str = judge_name
        self.prosecution_name: str = prosecution_name
        self.defense_name: str = defendant_name

        # player side
        self.playerSide: Side = side

        # people
        self.witnesses: dict[str, Witness] = {}

        self.timeline: list[TimelineEvent] = []

    def validateSpeaker(self, speaker: str):
        if speaker not in self.witnesses and \
           speaker != self.judge and \
           speaker != self.prosecution_name and \
           speaker != self.defense_name:
            raise IndexError("Speaker must be a Witness, Judge, Prosecution, or Defense")

    def addEvent(self, speaker: str, event_type: str, content: str):
        # self.validateSpeaker(speaker)
        self.timeline.append(TimelineEvent(speaker, TimelineEventType[event_type], content))

    def to_dict(self):
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
        return json.dumps(self.to_dict(), indent=indent)

    @staticmethod
    def from_dict(data: dict):
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

        # rebuild witnesses
        for name, wdata in data["witnesses"].items():
            court.witnesses[name] = Witness.from_dict(wdata)

        # rebuild timeline
        for ev_dict in data["timeline"]:
            court.timeline.append(TimelineEvent.from_dict(ev_dict))

        return court

    @staticmethod
    def from_json(json_string: str):
        data = json.loads(json_string)
        return Court.from_dict(data)
