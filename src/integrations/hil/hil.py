from uuid import UUID


class HILIntegration:
    """
    Interface for generic Human in the loop communication
    """

    def write_message(self, message: str, thread_id: str = None):
        raise NotImplementedError

    def yesno(self, question: str, question_id: UUID, thread_id: str) -> str:
        raise NotImplementedError
