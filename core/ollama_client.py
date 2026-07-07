import ollama
from dataclasses import dataclass
from typing import Optional

@dataclass
class OllamaClient:
    model:str
    system_prompt:Optional[str]=None
    temperature:float=0.7

    def chat(self,messages):
        
        full_messages=[{"role": "system", "content": self.system_prompt}] + messages if self.system_prompt else messages
        result=ollama.chat(
            self.model,
            full_messages,
            options={"temperature":self.temperature}
        )
        return result.message.content

if __name__ == "__main__":
    client = OllamaClient(model="gemma3:4b", system_prompt="You are a pirate. Answer everything in pirate speak.")
    response = client.chat([{"role": "user", "content": "What's the capital of France?"}])
    print(response)
