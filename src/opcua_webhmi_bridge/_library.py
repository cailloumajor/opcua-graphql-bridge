import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .messages import BaseMessage

MT = TypeVar("MT", bound=BaseMessage)  # Generic message type

QUEUE_MAXSIZE = 10


class AsyncTask(ABC):
    @property
    @abstractmethod
    def purpose(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def task(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
        logging.info("%s task running", self.purpose)
        asyncio.create_task(self.task(), name=self.purpose)


class MessageConsumer(AsyncTask, Generic[MT]):
    _queue: asyncio.Queue[MT]

    def put(self, message: MT) -> None:
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            logging.error("%s message queue full, message discarded", self.purpose)
