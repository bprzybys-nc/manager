from abc import ABC, abstractmethod

class CommunicationsChannel(ABC):

    @abstractmethod
    def send_message(self, thread_id: str, message: str):
        """Send a message to the user.
        Args:
            message: The message to send
            thread_id: The thread id to send the message to
        """
        pass

    @abstractmethod
    def send_question(self, thread_id: str, question: str, question_id: str):
        """Send a question to the user.
        Args:
            question: The question to send
            question_id: The question id to send
        """
        pass

    @abstractmethod
    def get_channel_type(self) -> str:
        """Get the type of communication channel.
        Returns:
            A string identifier for the channel type
        """
        pass

    @abstractmethod
    def create_thread(self, message: str) -> str:
        """Create a new conversation thread.
        Args:
            message: The initial message for the thread
        Returns:
            The thread id
        """
        pass