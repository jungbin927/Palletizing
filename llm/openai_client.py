# llm/openai_client.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

class OpenAIClient:
    """
    OpenAI API 호출 wrapper.

    역할:
    - API key 관리
    - 모델 호출
    - 응답 텍스트 반환
    """

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.0,
    ):
        api_key = os.getenv("OPENAI_API_KEY")

        print("[DEBUG OPENAI KEY EXISTS]", api_key is not None)
        if api_key:
            print("[DEBUG OPENAI KEY PREFIX]", api_key[:12])
            
        if api_key is None:
            raise ValueError(
                "OPENAI_API_KEY not set. "
                "Set environment variable first."
            )

        self.client = OpenAI(
            api_key=api_key
        )

        self.model = model
        self.temperature = temperature

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Chat completion 호출.

        Returns
        -------
        str
            모델 응답 텍스트
        """

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        text = response.choices[0].message.content

        return text