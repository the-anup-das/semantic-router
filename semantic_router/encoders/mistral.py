"""This file contains the MistralEncoder class which is used to encode text using MistralAI"""
import os
from time import sleep
from typing import List, Optional, Any


from semantic_router.encoders import BaseEncoder
from semantic_router.utils.defaults import EncoderDefault
from pydantic.v1 import PrivateAttr


class MistralEncoder(BaseEncoder):
    """Class to encode text using MistralAI"""

    _client: Any = PrivateAttr()
    _mistralai: Any = PrivateAttr()
    type: str = "mistral"

    def __init__(
        self,
        name: Optional[str] = None,
        mistralai_api_key: Optional[str] = None,
        score_threshold: float = 0.82,
    ):
        if name is None:
            name = EncoderDefault.MISTRAL.value["embedding_model"]
        super().__init__(name=name, score_threshold=score_threshold)
        (
            self._client,
            self._embedding_response,
            self._mistral_exception,
        ) = self._initialize_client(mistralai_api_key)

    def _initialize_client(self, api_key):
        try:
            from mistralai.client import MistralClient
            from mistralai.exceptions import MistralException
            from mistralai.models.embeddings import EmbeddingResponse
        except ImportError:
            raise ImportError(
                "Please install MistralAI to use MistralEncoder. "
                "You can install it with: "
                "`pip install 'semantic-router[mistralai]'`"
            )

        api_key = api_key or os.getenv("MISTRALAI_API_KEY")
        if api_key is None:
            raise ValueError("Mistral API key not provided")
        try:
            client = MistralClient(api_key=api_key)
            embedding_response = EmbeddingResponse
            mistral_exception = MistralException
        except Exception as e:
            raise ValueError(f"Unable to connect to MistralAI {e.args}: {e}") from e
        return client, embedding_response, mistral_exception

    def __call__(self, docs: List[str]) -> List[List[float]]:
        if self._client is None:
            raise ValueError("Mistral client not initialized")
        embeds = None
        error_message = ""

        # Exponential backoff
        for _ in range(3):
            try:
                embeds = self._client.embeddings(model=self.name, input=docs)
                if embeds.data:
                    break
            except self._mistral_exception as e:
                sleep(2**_)
                error_message = str(e)
            except Exception as e:
                raise ValueError(f"Unable to connect to MistralAI {e.args}: {e}") from e

        if (
            not embeds
            or not isinstance(embeds, self._embedding_response)
            or not embeds.data
        ):
            raise ValueError(f"No embeddings returned from MistralAI: {error_message}")
        embeddings = [embeds_obj.embedding for embeds_obj in embeds.data]
        return embeddings
