from typing import Callable, Sequence
from threading import Event as TEvent
from hhd.controller.base import Event, Consumer

callback: Callable | None = None
event = TEvent()

class LongpressConsumer(Consumer):
    available: bool = True
    def consume(self, events: Sequence[Event]):
        if not callback:
            return
        for ev in events:
            if ev["type"] == "button" and \
               ev["code"] == "pb_long" and \
               ev["value"] == True:
                event.set()
                callback()

instance = LongpressConsumer()
