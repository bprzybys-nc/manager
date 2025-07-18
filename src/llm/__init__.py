import os

from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    # temperature=0,
    deployment_name="gpt-4o",
    api_version="2024-10-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

class LLMUtils:
    def __init__(self, llm):
        self.llm = llm

    def secure_llm_call(self, prompt, retries=3):
        for _ in range(retries):
            try:
                return self.llm.invoke(prompt)
            except Exception as e:
                print(f"Error: {e}")
        raise Exception("Failed to get a valid response from the LLM")