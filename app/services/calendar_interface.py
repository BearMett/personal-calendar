from abc import ABC, abstractmethod
from typing import List, Dict


class CalendarInterface(ABC):
    @abstractmethod
    def get_events(self) -> List[Dict]:
        pass

    @abstractmethod
    def create_event(self, event: Dict) -> None:
        pass

    @abstractmethod
    def update_event(self, event_id: str, event: Dict) -> None:
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        pass
